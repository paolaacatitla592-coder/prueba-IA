import sys
import os
import time
import traceback
import json
import threading
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
log_visual("⚠️", "INIT", "AGENTE AUTÓNOMO V1: ADMINISTRADOR DE USUARIOS")
print("="*60 + "\n")

try:
    load_dotenv()

    # Credenciales de Render
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')

    if not all([GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
        log_visual("🔥", "ERROR", "Faltan credenciales críticas.")
        sys.exit(1)

    genai.configure(api_key=GOOGLE_API_KEY)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Configuración del modelo que elegiste
    model = genai.GenerativeModel("gemini-2.5-flash")
    CICLO_ANALISIS = 300 

    log_visual("🔗", "CONEXION", "Conectado a Supabase y Gemini.")

    def escanear_base_de_datos():
        try:
            respuesta = supabase.table('datos_prueba').select('*').limit(10).execute()
            return respuesta.data
        except Exception as e:
            log_visual("⚠️", "READ_ERR", f"Error leyendo base de datos: {e}")
            return None

    def ejecutar_orden_ia(ordenes_json):
        if not ordenes_json or "acciones" not in ordenes_json: 
            return

        for accion in ordenes_json["acciones"]:
            try:
                tipo = accion.get("tipo")
                id_objetivo = accion.get("id_objetivo")
                if tipo == "MODIFICAR" and id_objetivo:
                    nuevos_datos = accion.get("nuevos_datos", {})
                    supabase.table("datos_prueba").update(nuevos_datos).eq('id', id_objetivo).execute()
                    log_visual("✏️", "EXEC_UPD", f"ID {id_objetivo} actualizado a {nuevos_datos}.")
            except Exception as e:
                log_visual("❌", "EXEC_FAIL", f"Error en ejecución: {e}")

    # ==============================================================================
    # 2. CEREBRO ESTRATÉGICO
    # ==============================================================================
    def procesar_con_ia(datos):
        prompt = f"""
        Eres un administrador de usuarios. Analiza estos datos: {json.dumps(datos)}.
        Reglas:
        1. Si 'estado_cuenta' es 'pendiente' y 'ultima_actividad' es de junio 2026, cambia 'estado_cuenta' a 'activo'.
        2. Si 'ultima_actividad' es anterior a 2026-01-01, cambia 'estado_cuenta' a 'bloqueado'.
        
        Responde SOLO con un objeto JSON estrictamente válido y estructurado exactamente así, sin markdown ni explicaciones adicionales:
        {{
            "analisis_general": "Evaluación realizada",
            "acciones": [
                {{"tipo": "MODIFICAR", "id_objetivo": 1, "nuevos_datos": {{"estado_cuenta": "activo"}}}}
            ]
        }}
        """
        
        try:
            response = model.generate_content(prompt)
            texto_limpio = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(texto_limpio)
        except json.JSONDecodeError:
            log_visual("⚠️", "PARSE_ERR", "Gemini no devolvió un JSON válido.")
            return None

    # ==============================================================================
    # 3. BUCLE DE AUTONOMÍA
    # ==============================================================================
    def ciclo_autonomo():
        log_visual("⚡", "START", "Iniciando ciclo...")
        datos = escanear_base_de_datos()
        
        if datos:
            log_visual("🧠", "THINK", "Consultando a Gemini...")
            ordenes = procesar_con_ia(datos)
            if ordenes:
                ejecutar_orden_ia(ordenes)
        
        log_visual("💤", "WAIT", f"Reposo ({CICLO_ANALISIS}s)...")

    # ==============================================================================
    # 4. SERVIDOR FALSO PARA ENGAÑAR A RENDER (Solución al timeout)
    # ==============================================================================
    class ServidorFalso(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"El Agente Autonomo esta funcionando correctamente.")
            
        def log_message(self, format, *args):
            pass 

    def mantener_vivo():
        puerto = int(os.environ.get("PORT", 10000))
        server = HTTPServer(('0.0.0.0', puerto), ServidorFalso)
        log_visual("🌐", "WEB", f"Servidor falso abierto en el puerto {puerto} para Render")
        server.serve_forever()

    threading.Thread(target=mantener_vivo, daemon=True).start()

    while True:
        ciclo_autonomo()
        time.sleep(CICLO_ANALISIS)

except Exception as e:
    log_visual("💀", "FATAL", f"Error: {e}")
    traceback.print_exc()
