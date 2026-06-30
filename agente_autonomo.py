import sys
import os
import time
import json
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# ==============================================================================
# 1. CONFIGURACIÓN DEL ENTORNO
# ==============================================================================
sys.stdout.reconfigure(line_buffering=True)

def log_visual(emoji, estado, mensaje):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{emoji} [{timestamp}] {estado:<10} | {mensaje}", flush=True)

print("\n" + "="*60)
log_visual("⚠️", "INIT", "AGENTE AUTÓNOMO V1: ADMINISTRADOR Y SERVIDOR WEB")
print("="*60 + "\n")

try:
    load_dotenv()

    # Credenciales desde variables de entorno de Render
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')

    if not all([GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
        log_visual("🔥", "ERROR", "Faltan credenciales críticas en el entorno.")
        sys.exit(1)

    genai.configure(api_key=GOOGLE_API_KEY)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Modelo estable y rápido
    model = genai.GenerativeModel("gemini-1.5-flash")
    CICLO_ANALISIS = 300 

    log_visual("🔗", "CONEXION", "Conectado a Supabase y Gemini.")

    # ==========================================================================
    # 2. LÓGICA DEL AGENTE
    # ==========================================================================
    def escanear_base_de_datos():
        try:
            return supabase.table('datos_prueba').select('*').limit(10).execute().data
        except Exception as e:
            log_visual("⚠️", "READ_ERR", f"Error base de datos: {e}")
            return None

    def procesar_con_ia(datos):
        prompt = f"""Analiza estos datos: {json.dumps(datos)}. 
        Si 'estado_cuenta' es 'pendiente', cámbialo a 'activo'.
        Responde SOLO con JSON: {{"acciones": [{{"tipo": "MODIFICAR", "id_objetivo": 1, "nuevos_datos": {{"estado_cuenta": "activo"}}}} ]}}"""
        try:
            response = model.generate_content(prompt)
            return json.loads(response.text.replace('```json', '').replace('```', '').strip())
        except: return None

    # ==========================================================================
    # 3. SERVIDOR WEB Y CONFIGURACIÓN (Para Render y Frontend)
    # ==========================================================================
    class ServidorFalso(BaseHTTPRequestHandler):
        def do_GET(self):
            # Endpoint para que tu página web pida las credenciales de forma segura
            if self.path == '/config':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*') # CORS habilitado
                self.end_headers()
                config = json.dumps({"url": SUPABASE_URL, "key": SUPABASE_KEY})
                self.wfile.write(config.encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Servidor del Agente Activo.")
        
        def log_message(self, format, *args):
            pass # Silenciamos los logs de peticiones HTTP para que no saturen

    def mantener_vivo():
        puerto = int(os.environ.get("PORT", 10000))
        server = HTTPServer(('0.0.0.0', puerto), ServidorFalso)
        log_visual("🌐", "WEB", f"Servidor activo en puerto {puerto}")
        server.serve_forever()

    threading.Thread(target=mantener_vivo, daemon=True).start()

    # ==========================================================================
    # 4. BUCLE PRINCIPAL
    # ==========================================================================
    while True:
        log_visual("⚡", "CICLO", "Ejecutando agente...")
        datos = escanear_base_de_datos()
        if datos:
            ordenes = procesar_con_ia(datos)
            # (Aquí iría la lógica de ejecución de órdenes)
        time.sleep(CICLO_ANALISIS)

except Exception as e:
    log_visual("💀", "FATAL", f"Error crítico: {e}")
    traceback.print_exc()
