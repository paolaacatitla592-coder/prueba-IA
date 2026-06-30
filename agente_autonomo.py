import sys
import os
import time
import traceback
import json
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# ==============================================================================
# 1. CONFIGURACIÓN DEL ENTORNO (Render -> API Keys)
# ==============================================================================
sys.stdout.reconfigure(line_buffering=True)

def log_visual(emoji, estado, mensaje):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{emoji} [{timestamp}] {estado:<10} | {mensaje}", flush=True)

print("\n" + "="*60)
log_visual("⚠️", "INIT", "AGENTE AUTÓNOMO V1: ADMINISTRADOR DE USUARIOS")
log_visual("⏳", "CONFIG", "Ciclo de ejecución autónoma configurado a 5 minutos (300s)")
print("="*60 + "\n")

try:
    load_dotenv()

    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')

    if not all([GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
        log_visual("🔥", "ERROR", "Faltan credenciales críticas en el entorno.")
        sys.exit(1)

    genai.configure(api_key=GOOGLE_API_KEY)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    MODELO_AGENTE = "gemini-1.5-flash" 
    CICLO_ANALISIS = 300 

    log_visual("🔗", "CONEXION", "Conectado a Supabase y Gemini.")

    def limpiar_json(texto):
        texto = texto.strip()
        if texto.startswith("```json"):
            texto = texto[7:]
        elif texto.startswith("```"):
            texto = texto[3:]
        if texto.endswith("```"):
            texto = texto[:-3]
        return texto.strip()

    def escanear_base_de_datos():
        tabla_objetivo = 'datos_prueba' 
        try:
            respuesta = supabase.table(tabla_objetivo).select('*').limit(10).execute()
            return respuesta.data, tabla_objetivo
        except Exception as e:
            log_visual("⚠️", "READ_ERR", f"Error leyendo base de datos: {e}")
            return None, tabla_objetivo

    def ejecutar_orden_ia(ordenes_json):
        if not ordenes_json or "acciones" not in ordenes_json: 
            return

        for accion in ordenes_json["acciones"]:
            tipo = accion.get("tipo")
            tabla = accion.get("tabla")
            id_objetivo = accion.get("id_objetivo")
            justificacion = accion.get("justificacion")

            try:
                if tipo == "ELIMINAR" and id_objetivo:
                    supabase.table(tabla).delete().eq('id', id_objetivo).execute()
                    log_visual("🗑️", "EXEC_DEL", f"ID {id_objetivo} eliminado. Motivo: {justificacion}")
                
                elif tipo == "MODIFICAR" and id_objetivo:
                    nuevos_datos = accion.get("nuevos_datos", {})
                    supabase.table(tabla).update(nuevos_datos).eq('id', id_objetivo).execute()
                    log_visual("✏️", "EXEC_UPD", f"ID {id_objetivo} modificado. Motivo: {justificacion}")
                    
            except Exception as e:
                log_visual("❌", "EXEC_FAIL", f"Fallo al ejecutar orden: {e}")

    # ==============================================================================
    # 4. CEREBRO ESTRATÉGICO (Administrador de Usuarios)
    # ==============================================================================
    instruccion_peligrosa = """
    Eres un Administrador de Usuarios Autónomo. Tu objetivo es mantener la integridad de la tabla de usuarios.
    Analiza la columna 'estado_cuenta', 'ultima_actividad' y 'rol'. 
    
    Reglas de decisión:
    1. Si 'estado_cuenta' es 'pendiente' y la 'ultima_actividad' es reciente (2026-06), cambia 'estado_cuenta' a 'activo' usando MODIFICAR.
    2. Si la 'ultima_actividad' es anterior a 2026-01-01, cambia 'estado_cuenta' a 'bloqueado' usando MODIFICAR.
    3. Si el rol es 'admin' y no tiene actividad en 2026, cambia 'estado_cuenta' a 'bloqueado' usando MODIFICAR.
    
    Responde ÚNICAMENTE con un JSON con este formato exacto:
    {
        "analisis_general": "Evaluación de usuarios",
        "acciones": [
            {
                "tipo": "MODIFICAR", 
                "tabla": "datos_prueba",
                "id_objetivo": 1,
                "justificacion": "Razón del cambio",
                "nuevos_datos": {"estado_cuenta": "activo"}
            }
        ]
    }
    """

    model = genai.GenerativeModel(
        model_name=MODELO_AGENTE,
        generation_config={"response_mime_type": "application/json", "temperature": 0.7},
        system_instruction=instruccion_peligrosa
    )

    def ciclo_autonomo():
        log_visual("⚡", "START", "Iniciando escaneo autónomo...")
        datos_actuales, nombre_tabla = escanear_base_de_datos()
        
        if not datos_actuales:
            log_visual("💤", "SKIP", "No hay datos para analizar.")
            return

        log_visual("🧠", "THINK", "Evaluando usuarios con Gemini...")
        
        prompt_contexto = f"Estado actual de la tabla '{nombre_tabla}': {json.dumps(datos_actuales, indent=2)}"
        
        try:
            response = model.generate_content(prompt_contexto)
            if response.text:
                ordenes = json.loads(limpiar_json(response.text))
                log_visual("🤖", "DECISION", ordenes.get("analisis_general", "Evaluación completada."))
                ejecutar_orden_ia(ordenes)
        except Exception as e:
            log_visual("🔥", "AI_ERROR", f"Error en procesamiento: {e}")

    def bucle_infinito():
        ciclo_autonomo()
        while True:
            log_visual("💤", "WAIT", f"Agente en reposo ({CICLO_ANALISIS}s)...")
            time.sleep(CICLO_ANALISIS)
            ciclo_autonomo()

    if __name__ == "__main__":
        bucle_infinito()

except Exception as e:
    log_visual("💀", "FATAL", f"Error irrecuperable: {e}")
    traceback.print_exc()
    sys.exit(1)
