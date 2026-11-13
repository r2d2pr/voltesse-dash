"""Real authenticated API for the laptop Technician GUI.

Existing driver application remains independent. DATABASE mode reads its schema.
SIMULATION mode reuses the Streamlit formulas, explicitly labeled in every response.
"""
import asyncio
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import tempfile
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Any

import jwt
import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from .config import Settings
from .simulator import live_metrics, live_temperature_history

HASHER = PasswordHasher()  # Argon2id, unique cryptographic salt per password
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))
COOKIE = 'voltesse_session'
ISSUER = 'voltesse-technician'

class Login(BaseModel):
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=1024)

class Preferences(BaseModel):
    warning_temp: int = Field(default=160, ge=100, le=250)
    warning_battery: int = Field(default=20, ge=5, le=40)
    palette: str = Field(default='mint')

class VehicleCommand(BaseModel):
    action: str = Field(min_length=1, max_length=64)
    value: Any = None
    enabled: bool | None = None
    code: str | None = None
    desc: str | None = None


def connect(settings):
    return psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=5, prepare_threshold=None)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_for(settings, token_id):
    return hmac.new(settings.secret.encode(), ('csrf:' + token_id).encode(), hashlib.sha256).hexdigest()


class TelemetryUDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_frame):
        self.on_frame = on_frame

    def datagram_received(self, data: bytes, addr):
        try:
            msg = json.loads(data.decode("utf-8"))
            self.on_frame(msg)
        except Exception:
            pass


def create_app(settings: Settings | None = None):
    settings = settings or Settings.from_env()

    # In-memory real-time state (<15ms latency push)
    latest_live: dict | None = None
    last_udp_time: float = 0.0
    trace_ring_buffer: deque = deque(maxlen=60)
    active_websockets: set[WebSocket] = set()

    async def broadcast_ws(frame_dict: dict):
        if not active_websockets:
            return
        payload = json.dumps(frame_dict)
        dead = set()
        for ws in list(active_websockets):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.add(ws)
        active_websockets.difference_update(dead)

    def on_udp_frame(frame: dict):
        nonlocal latest_live, last_udp_time
        now = time.time()
        latest_live = frame
        last_udp_time = now
        mot_temp_f = frame.get("motor_temp_f", frame.get("temperature", 0.0))
        trace_ring_buffer.append({
            "seconds": round(now % 60, 1),
            "speed": frame.get("speed", 0.0),
            "rpm": frame.get("rpm", 0),
            "throttle": frame.get("throttle_pct", 0.0),
            "brake": frame.get("brake_pct", 0.0),
            "power_kw": frame.get("power_kw", round(frame.get("power", 0) / 1000.0, 2)),
            "temperature": mot_temp_f,
        })
        live_payload = {
            "mode": frame.get("mode", "RACE"),
            "status": "LIVE (F1 STREAM · 20 Hz)",
            "stale": False,
            "source_type": "LIVE_UDP",
            "timestamp": datetime.fromtimestamp(frame.get("timestamp", now), tz=timezone.utc).isoformat(),
            "metrics": {
                "speed": frame.get("speed", 0.0),
                "rpm": frame.get("rpm", 0),
                "battery": frame.get("battery", 0.0),
                "temperature": mot_temp_f,
                "motor_temp_f": mot_temp_f,
                "inverter_temp_f": frame.get("inverter_temp_f", 0.0),
                "battery_temp_f": frame.get("battery_temp_f", 0.0),
                "power": frame.get("power", 0),
                "power_kw": frame.get("power_kw", round(frame.get("power", 0) / 1000.0, 2)),
                "voltage": frame.get("voltage", 0.0),
                "current": frame.get("current", 0.0),
                "throttle_pct": frame.get("throttle_pct", 0.0),
                "brake_pct": frame.get("brake_pct", 0.0),
                "gear": frame.get("gear", "D"),
                "transmission_mode": frame.get("transmission_mode", "AUTO"),
                "drive_mode": frame.get("drive_mode", "DRIVE"),
                "est_range_mi": frame.get("est_range_mi", 0),
                "pit_limiter": frame.get("pit_limiter", False),
                "power_limit_pct": frame.get("power_limit_pct", 100.0),
                "warnings": frame.get("warnings", []),
            },
            "history": list(trace_ring_buffer)
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(broadcast_ws(live_payload))
        except Exception:
            pass

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        loop = asyncio.get_running_loop()
        transport = None
        try:
            transport, _ = await loop.create_datagram_endpoint(
                lambda: TelemetryUDPProtocol(on_udp_frame),
                local_addr=("127.0.0.1", 9871)
            )
        except Exception:
            pass
        yield
        if transport:
            transport.close()

    app = FastAPI(title='Voltesse Technician API', docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings = settings

    @app.middleware('http')
    async def security_headers(request, call_next):
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.url.path.startswith('/api/'):
            origin = request.headers.get('origin')
            host = request.headers.get('host')
            is_same_host = bool(origin and host and (origin == f'http://{host}' or origin == f'https://{host}'))
            if not is_same_host and '*' not in settings.origins and (origin and origin not in settings.origins):
                return JSONResponse({'detail': 'Untrusted request origin.'}, status_code=403)
            if request.headers.get('x-requested-with') != 'VoltesseGUI':
                return JSONResponse({'detail': 'Missing application request header.'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Frame-Options'] = 'DENY'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        if settings.secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.exception_handler(psycopg.Error)
    async def database_error(request, exc):
        # Never leak DSNs, SQL, or credentials to a browser.
        return JSONResponse({'detail': 'Database unavailable. Check backend configuration.'}, status_code=503)

    def current_user(request: Request):
        try:
            claims = jwt.decode(request.cookies.get(COOKIE, ''), settings.secret,
                                algorithms=['HS256'], issuer=ISSUER, audience='technician-gui',
                                options={'require': ['exp', 'iat', 'jti', 'sub']})
            uid = int(claims['sub'])
            token_id = claims['jti']
            if not isinstance(token_id, str):
                raise ValueError('Invalid token ID')
        except (jwt.PyJWTError, ValueError, TypeError):
            raise HTTPException(401, 'Please sign in.')
        with connect(settings) as conn:
            user = conn.execute('''SELECT u.technician_id, u.username, u.name, u.role
                FROM web_auth_session s JOIN technician_user u USING (technician_id)
                WHERE s.token_hash=%s AND s.technician_id=%s AND s.expires_at > now()''',
                (digest(token_id), uid)).fetchone()
        if not user:
            raise HTTPException(401, 'Session expired. Please sign in.')
        if user['role'] not in ('ADMIN', 'TECHNICIAN'):
            raise HTTPException(403, 'Technician access required.')
        if request.method not in ('GET', 'HEAD'):
            if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), csrf_for(settings, token_id)):
                raise HTTPException(403, 'Invalid request token.')
        user['token_id'] = token_id
        return user

    User = Annotated[dict, Depends(current_user)]

    @app.get('/api/health')
    def health():
        return {'status': 'ok'}

    @app.post('/api/auth/login')
    def login(body: Login, request: Request, response: Response):
        username = body.username.strip().lower()
        # Account + IP buckets are persisted, bounded, and locked before checking passwords.
        # Ignore forwarded IP headers: local proxy traffic shares a conservative IP limit.
        ip = request.client.host if request.client else 'unknown'
        buckets = sorted([(digest('user:' + username), 5), (digest('ip:' + ip), 30)])
        error = None
        user = None
        with connect(settings) as conn:
            conn.execute("DELETE FROM web_login_throttle WHERE window_start < now() - interval '15 minutes'")
            conn.execute('DELETE FROM web_auth_session WHERE expires_at <= now()')
            locked = []
            for key, limit in buckets:
                conn.execute('INSERT INTO web_login_throttle(bucket,attempts) VALUES (%s,0) ON CONFLICT DO NOTHING', (key,))
                row = conn.execute('SELECT * FROM web_login_throttle WHERE bucket=%s FOR UPDATE', (key,)).fetchone()
                locked.append((row, limit))
            if any(row['attempts'] >= limit for row, limit in locked):
                error = 429
            else:
                user = conn.execute('SELECT * FROM technician_user WHERE username=%s', (username,)).fetchone()
                try:
                    valid = HASHER.verify(user['password_hash'] if user else DUMMY_HASH, body.password)
                except (VerificationError, InvalidHashError):
                    valid = False
                if not user or not valid or user['role'] not in ('ADMIN', 'TECHNICIAN'):
                    for key, _ in buckets:
                        conn.execute('UPDATE web_login_throttle SET attempts=attempts+1 WHERE bucket=%s', (key,))
                    error = 401
                else:
                    conn.execute('DELETE FROM web_login_throttle WHERE bucket=%s', (digest('user:' + username),))
                    conn.execute('UPDATE technician_user SET last_login_at=now() WHERE technician_id=%s', (user['technician_id'],))
                    if HASHER.check_needs_rehash(user['password_hash']):
                        conn.execute('UPDATE technician_user SET password_hash=%s WHERE technician_id=%s',
                                     (HASHER.hash(body.password), user['technician_id']))
                    token_id = secrets.token_urlsafe(32)
                    now = datetime.now(timezone.utc)
                    expiry = now + timedelta(minutes=settings.minutes)
                    conn.execute('INSERT INTO web_auth_session VALUES (%s,%s,%s)',
                                 (digest(token_id), user['technician_id'], expiry))
        # Raise outside the transaction so failures persist.
        if error == 429:
            raise HTTPException(429, 'Too many sign-in attempts. Try again in 15 minutes.', headers={'Retry-After': '900'})
        if error:
            raise HTTPException(401, 'Incorrect username or password.')
        token = jwt.encode({'sub': str(user['technician_id']), 'jti': token_id, 'iat': now, 'exp': expiry,
                            'iss': ISSUER, 'aud': 'technician-gui'}, settings.secret, algorithm='HS256')
        response.set_cookie(COOKIE, token, max_age=settings.minutes * 60, httponly=True,
                            secure=settings.secure, samesite='strict', path='/api')
        return {'username': user['username'], 'name': user['name'], 'role': user['role'],
                'csrf_token': csrf_for(settings, token_id)}

    @app.get('/api/auth/me')
    def me(user: User):
        return {k: user[k] for k in ('username', 'name', 'role')} | {'csrf_token': csrf_for(settings, user['token_id'])}

    @app.post('/api/auth/logout')
    def logout(response: Response, user: User):
        with connect(settings) as conn:
            conn.execute('DELETE FROM web_auth_session WHERE token_hash=%s', (digest(user['token_id']),))
        response.delete_cookie(COOKIE, path='/api', secure=settings.secure, httponly=True, samesite='strict')
        return {'ok': True}

    @app.get('/api/settings')
    def get_settings(user: User):
        with connect(settings) as conn:
            row = conn.execute('SELECT warning_temp,warning_battery,palette FROM technician_preferences WHERE technician_id=%s',
                               (user['technician_id'],)).fetchone()
        return row or {'warning_temp': 160, 'warning_battery': 20, 'palette': 'mint'}

    @app.put('/api/settings')
    def put_settings(body: Preferences, user: User):
        with connect(settings) as conn:
            conn.execute('''INSERT INTO technician_preferences (technician_id, warning_temp, warning_battery, palette)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (technician_id) DO UPDATE SET warning_temp=EXCLUDED.warning_temp,
                warning_battery=EXCLUDED.warning_battery,
                palette=EXCLUDED.palette''',
                (user['technician_id'], body.warning_temp, body.warning_battery, body.palette))
        return body

    @app.post('/api/vehicle/command')
    def send_vehicle_command(cmd: VehicleCommand, user: User):
        import socket
        payload = json.dumps(cmd.model_dump(exclude_none=True)).encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(payload, ("127.0.0.1", 9872))
            return {"status": "DISPATCHED", "command": cmd.model_dump(exclude_none=True)}
        except Exception as e:
            raise HTTPException(503, f"Vehicle command dispatch failed: {e}")
        finally:
            sock.close()

    @app.websocket('/api/ws/telemetry')
    async def ws_telemetry(websocket: WebSocket):
        await websocket.accept()
        active_websockets.add(websocket)
        now = time.time()
        if latest_live and (now - last_udp_time) <= 3.0:
            mot_temp_f = latest_live.get("motor_temp_f", latest_live.get("temperature", 0.0))
            init_payload = {
                "mode": latest_live.get("mode", "RACE"),
                "status": "LIVE (F1 STREAM · 20 Hz)",
                "stale": False,
                "source_type": "LIVE_UDP",
                "timestamp": datetime.fromtimestamp(latest_live.get("timestamp", now), tz=timezone.utc).isoformat(),
                "metrics": {
                    "speed": latest_live.get("speed", 0.0),
                    "rpm": latest_live.get("rpm", 0),
                    "battery": latest_live.get("battery", 0.0),
                    "temperature": mot_temp_f,
                    "motor_temp_f": mot_temp_f,
                    "inverter_temp_f": latest_live.get("inverter_temp_f", 0.0),
                    "battery_temp_f": latest_live.get("battery_temp_f", 0.0),
                    "power": latest_live.get("power", 0),
                    "power_kw": latest_live.get("power_kw", round(latest_live.get("power", 0) / 1000.0, 2)),
                    "voltage": latest_live.get("voltage", 0.0),
                    "current": latest_live.get("current", 0.0),
                    "throttle_pct": latest_live.get("throttle_pct", 0.0),
                    "brake_pct": latest_live.get("brake_pct", 0.0),
                    "gear": latest_live.get("gear", "D"),
                    "transmission_mode": latest_live.get("transmission_mode", "AUTO"),
                    "drive_mode": latest_live.get("drive_mode", "DRIVE"),
                    "est_range_mi": latest_live.get("est_range_mi", 0),
                    "pit_limiter": latest_live.get("pit_limiter", False),
                    "power_limit_pct": latest_live.get("power_limit_pct", 100.0),
                    "warnings": latest_live.get("warnings", []),
                },
                "history": list(trace_ring_buffer)
            }
            try:
                await websocket.send_text(json.dumps(init_payload))
            except Exception:
                pass
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            active_websockets.discard(websocket)

    @app.get('/api/live')
    def live(user: User, t: int = Query(default=30, ge=0, le=120)):
        if settings.mode == 'SIMULATION':
            values = live_metrics(t)
            times, temps = live_temperature_history(t)
            mot_f = round(values['temperature'] * 9.0 / 5.0 + 32.0, 1)
            power_w = round(values['speed'] * 180)
            return {'mode': 'SIMULATION', 'status': 'Simulated vehicle data', 'stale': False,
                    'metrics': {
                        'speed': values['speed'],
                        'rpm': values['rpm'],
                        'battery': values['battery'],
                        'temperature': mot_f,
                        'motor_temp_f': mot_f,
                        'inverter_temp_f': round(mot_f - 12.0, 1),
                        'battery_temp_f': round(mot_f - 24.0, 1),
                        'power': power_w,
                        'power_kw': round(power_w / 1000.0, 2),
                        'voltage': 382.0,
                        'current': round(power_w / 382.0, 1),
                        'throttle_pct': round(min(100.0, values['speed'] * 1.2), 1),
                        'brake_pct': 0.0,
                        'gear': 'D',
                        'transmission_mode': 'AUTO',
                        'drive_mode': 'DRIVE',
                        'est_range_mi': int(round(values['battery'] * 2.6)),
                    },
                    'history': [{'seconds': x, 'temperature': round(y * 9.0 / 5.0 + 32.0, 1),
                                 'speed': values['speed'], 'rpm': values['rpm'],
                                 'throttle': round(min(100.0, values['speed'] * 1.2), 1), 'brake': 0.0,
                                 'power_kw': round(power_w / 1000.0, 2)} for x, y in zip(times, temps)],
                    'timestamp': None}

        # Fast path: in-memory live UDP stream (<15ms latency, zero DB load)
        now_ts = time.time()
        if latest_live and (now_ts - last_udp_time) <= 3.0:
            mot_temp_f = latest_live.get("motor_temp_f", latest_live.get("temperature", 0.0))
            return {
                'mode': latest_live.get('mode', 'DATABASE'),
                'status': 'LIVE (F1 STREAM · 20 Hz)',
                'stale': False,
                'timestamp': datetime.fromtimestamp(latest_live.get('timestamp', now_ts), tz=timezone.utc).isoformat(),
                'source_type': 'LIVE_UDP',
                'history': list(trace_ring_buffer),
                'metrics': {
                    'speed': latest_live.get('speed', 0.0),
                    'rpm': latest_live.get('rpm', 0),
                    'battery': latest_live.get('battery', 0.0),
                    'temperature': mot_temp_f,
                    'motor_temp_f': mot_temp_f,
                    'inverter_temp_f': latest_live.get('inverter_temp_f', 0.0),
                    'battery_temp_f': latest_live.get('battery_temp_f', 0.0),
                    'power': latest_live.get('power', 0),
                    'power_kw': latest_live.get('power_kw', round(latest_live.get('power', 0) / 1000.0, 2)),
                    'voltage': latest_live.get('voltage', 0.0),
                    'current': latest_live.get('current', 0.0),
                    'throttle_pct': latest_live.get('throttle_pct', 0.0),
                    'brake_pct': latest_live.get('brake_pct', 0.0),
                    'gear': latest_live.get('gear', 'D'),
                    'transmission_mode': latest_live.get('transmission_mode', 'AUTO'),
                    'drive_mode': latest_live.get('drive_mode', 'DRIVE'),
                    'est_range_mi': latest_live.get('est_range_mi', 0),
                    'pit_limiter': latest_live.get('pit_limiter', False),
                    'power_limit_pct': latest_live.get('power_limit_pct', 100.0),
                    'warnings': latest_live.get('warnings', []),
                }
            }

        # Standby fallback: read newest from PostgreSQL using fast indexed query
        with connect(settings) as conn:
            latest = conn.execute('''SELECT t.*, s.source_type FROM telemetry_log t JOIN vehicle_session s USING (session_id)
                WHERE t.log_id = (SELECT max(log_id) FROM telemetry_log WHERE signal_status IS DISTINCT FROM 'FIGMA DEMO')''').fetchone()
            if not latest:
                return {'mode': 'DATABASE', 'status': 'No vehicle readings available', 'metrics': None, 'history': [], 'stale': True}
            rows = conn.execute('''SELECT extract(epoch FROM ("timestamp" - %s::timestamptz)) AS seconds,
                round((motor_temperature * 9.0 / 5.0) + 32.0, 1) AS temperature,
                speed_mph AS speed, motor_rpm AS rpm, coalesce(throttle_pct, 0.0) AS throttle,
                coalesce(brake_pct, 0.0) AS brake, round(power_draw_watts / 1000.0, 2) AS power_kw
                FROM telemetry_log WHERE session_id=%s
                AND "timestamp" BETWEEN %s::timestamptz - interval '60 seconds' AND %s::timestamptz
                ORDER BY "timestamp"''', (latest['timestamp'], latest['session_id'], latest['timestamp'], latest['timestamp'])).fetchall()
        stale = (datetime.now(timezone.utc) - latest['timestamp']).total_seconds() > 5
        mot_f = round(latest['motor_temperature'] * 9.0 / 5.0 + 32.0, 1) if latest['motor_temperature'] is not None else 0.0
        inv_c = latest['inverter_temp_c'] if 'inverter_temp_c' in latest and latest['inverter_temp_c'] is not None else None
        bat_c = latest['battery_temp_c'] if 'battery_temp_c' in latest and latest['battery_temp_c'] is not None else None
        inv_f = round(inv_c * 9.0 / 5.0 + 32.0, 1) if inv_c is not None else round(mot_f - 10.0, 1)
        bat_f = round(bat_c * 9.0 / 5.0 + 32.0, 1) if bat_c is not None else round(mot_f - 22.0, 1)
        power_w = float(latest['power_draw_watts'] or 0.0)
        power_kw = round(power_w / 1000.0, 2)
        soc = float(latest['battery_percent'] or 0.0)
        est_range_mi = int(round(soc * 2.6))
        return {'mode': 'DATABASE', 'status': latest['signal_status'] or 'Database telemetry', 'stale': stale,
                'timestamp': latest['timestamp'], 'source_type': latest['source_type'], 'history': rows,
                'metrics': {'speed': latest['speed_mph'], 'rpm': latest['motor_rpm'], 'battery': latest['battery_percent'],
                            'temperature': mot_f, 'motor_temp_f': mot_f, 'inverter_temp_f': inv_f, 'battery_temp_f': bat_f,
                            'power': power_w, 'power_kw': power_kw,
                            'voltage': round(float(latest['battery_voltage_v'] or 0.0), 1) if 'battery_voltage_v' in latest else 0.0,
                            'current': round(float(latest['battery_current_a'] or 0.0), 1) if 'battery_current_a' in latest else 0.0,
                            'throttle_pct': round(float(latest['throttle_pct'] or 0.0), 1) if 'throttle_pct' in latest else 0.0,
                            'brake_pct': round(float(latest['brake_pct'] or 0.0), 1) if 'brake_pct' in latest else 0.0,
                            'gear': latest.get('gear') or 'D',
                            'transmission_mode': latest.get('transmission_mode') or 'AUTO',
                            'drive_mode': latest.get('drive_mode') or 'DRIVE',
                            'est_range_mi': est_range_mi}}

    @app.get('/api/sessions')
    def sessions(user: User):
        with connect(settings) as conn:
            return conn.execute('''SELECT s.session_id AS id, s.driver_identifier, s.start_timestamp,
                s.source_type, s.status, extract(epoch FROM (coalesce(s.end_timestamp, now())-s.start_timestamp)) AS duration_seconds,
                max(t.motor_temperature) AS max_temp, count(t.log_id) AS sample_count
                FROM vehicle_session s LEFT JOIN telemetry_log t USING(session_id)
                GROUP BY s.session_id ORDER BY s.start_timestamp DESC LIMIT 20''').fetchall()

    @app.get('/api/sessions/{session_id}/diagnostics')
    def diagnostics(session_id: int, user: User):
        with connect(settings) as conn:
            session = conn.execute('SELECT session_id,source_type,status FROM vehicle_session WHERE session_id=%s', (session_id,)).fetchone()
            if not session:
                raise HTTPException(404, 'Session not found.')
            # Aggregated SQL views from the existing project schema; no invented trend lines.
            charts = {}
            for key, view, x, y in [
                ('efficiency', 'v_efficiency_by_speed', 'speed_bucket_mph', 'wh_per_mile'),
                ('power_temp', 'v_power_by_temperature', 'temperature_bucket_c', 'avg_power_watts'),
                ('battery', 'v_battery_over_distance', 'trip_distance_km', 'battery_percent'),
                ('power_rpm', 'v_power_by_rpm', 'rpm_bucket', 'avg_power_watts'),
                ('temperature', 'v_temperature_over_time', 'seconds_into_session', 'motor_temperature'),
            ]:
                # Identifiers are constants above, never supplied by the client.
                rows = conn.execute(f'SELECT {x} AS x, {y} AS y FROM {view} WHERE session_id=%s ORDER BY {x} LIMIT 2000',
                                    (session_id,)).fetchall()
                if key == 'battery':
                    rows = [{'x': float(r['x']) / 1.609344, 'y': r['y']} for r in rows]
                if key == 'temperature':
                    rows = [{'x': float(r['x']) / 60, 'y': r['y']} for r in rows]
                charts[key] = rows
        return {'session': session, 'charts': charts}

    @app.get('/api/backups')
    def backups(user: User):
        with connect(settings) as conn:
            return conn.execute('''SELECT backup_id, backup_timestamp,backup_status,backup_type
                FROM backup_log ORDER BY backup_timestamp DESC LIMIT 20''').fetchall()

    @app.post('/api/backups', status_code=201)
    def backup(user: User):
        directory = settings.backup_dir
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with connect(settings) as conn:
            # Separate connection held for the duration: serialize resource-heavy backups.
            if not conn.execute('SELECT pg_try_advisory_lock(947261) AS locked').fetchone()['locked']:
                raise HTTPException(409, 'A backup is already running.')
            backup_id = conn.execute("INSERT INTO backup_log(backup_type,initiated_by) VALUES ('MANUAL',%s) RETURNING backup_id",
                                     (user['technician_id'],)).fetchone()['backup_id']
            conn.commit()
            path = None
            try:
                fd, name = tempfile.mkstemp(prefix=f'voltesse_{backup_id}_', suffix='.dump', dir=directory)
                os.close(fd)  # mkstemp uses 0600 permissions
                path = Path(name)
                info = conninfo_to_dict(settings.database_url)
                env = os.environ.copy()
                mapping = {'host':'PGHOST','port':'PGPORT','user':'PGUSER','password':'PGPASSWORD',
                           'dbname':'PGDATABASE','sslmode':'PGSSLMODE','sslrootcert':'PGSSLROOTCERT',
                           'sslcert':'PGSSLCERT','sslkey':'PGSSLKEY'}
                for key, value in info.items():
                    if key in mapping:
                        env[mapping[key]] = value
                env['PGCONNECT_TIMEOUT'] = '5'
                subprocess.run(['pg_dump', '--format=custom', '--no-owner', '--file', str(path)],
                               env=env, check=True, capture_output=True, timeout=120)
                conn.execute("UPDATE backup_log SET backup_status='SUCCESS',file_reference=%s WHERE backup_id=%s", (path.name, backup_id))
                conn.commit()
            except (OSError, subprocess.SubprocessError):
                if path:
                    path.unlink(missing_ok=True)
                conn.execute("UPDATE backup_log SET backup_status='FAILED' WHERE backup_id=%s", (backup_id,))
                conn.commit()
                raise HTTPException(503, 'Backup failed. Check pg_dump installation and database connectivity on the backend host.')
            finally:
                conn.execute('SELECT pg_advisory_unlock(947261)')
        return {'backup_id': backup_id, 'backup_status': 'SUCCESS'}

    dist = os.getenv('WEB_DIST')
    if dist:
        app.mount('/', StaticFiles(directory=Path(dist), html=True), name='web')
    return app
