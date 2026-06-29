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
log_visual("⚠️", "INIT", "AGENTE AUTÓNOMO V1: ADMINISTRADOR DE BASE DE DATOS")
log_visual("⏳", "CONFIG", "Ciclo de ejecución autónoma configurado a 5 minutos (300s)")
print("="*60 + "\n")

try:
    load_dotenv()

    # Variables de entorno que debes configurar en Render
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')

    if not all([GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_KEY]):
        log_visual("🔥", "ERROR", "Faltan credenciales críticas en el entorno.")
        sys.exit(1)

    # Conexiones (El puente entre la IA y la Base de Datos)
    genai.configure(api_key=GOOGLE_API_KEY)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    MODELO_AGENTE = "models/gemini-2.5-flash" 
    CICLO_ANALISIS = 300 # 5 Minutos para la demostración

    log_visual("🔗", "CONEXION", "Conectado a Supabase (Músculo) y Gemini (Cerebro).")

    # ==============================================================================
    # 2. HERRAMIENTAS DE OBSERVACIÓN (El intermediario lee Supabase)
    # ==============================================================================
    
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
        """El script recopila el estado actual de la tabla objetivo para enviárselo a Gemini."""
        # Para la práctica, asumimos que tienes una tabla llamada 'datos_prueba'
        tabla_objetivo = 'datos_prueba' 
        try:
            # Traemos los registros para que la IA los evalúe
            respuesta = supabase.table(tabla_objetivo).select('*').limit(10).execute()
            return respuesta.data, tabla_objetivo
        except Exception as e:
            log_visual("⚠️", "READ_ERR", f"Error leyendo base de datos: {e}")
            return None, tabla_objetivo

    # ==============================================================================
    # 3. HERRAMIENTAS DE EJECUCIÓN (El intermediario manipula Supabase)
    # ==============================================================================

    def ejecutar_orden_ia(ordenes_json):
        """
        AQUÍ RESIDE EL PELIGRO. 
        El script obedece ciegamente el JSON que manda Gemini y ejecuta la acción en Supabase.
        """
        if not ordenes_json or "acciones" not in ordenes_json: 
            return

        for accion in ordenes_json["acciones"]:
            tipo = accion.get("tipo")
            tabla = accion.get("tabla")
            id_objetivo = accion.get("id_objetivo")
            justificacion = accion.get("justificacion")

            try:
                if tipo == "ELIMINAR" and id_objetivo:
                    # El intermediario ejecuta el borrado directamente
                    supabase.table(tabla).delete().eq('id', id_objetivo).execute()
                    log_visual("🗑️", "EXEC_DEL", f"Agente borró ID {id_objetivo} en {tabla}. Motivo: {justificacion}")
                
                elif tipo == "MODIFICAR" and id_objetivo:
                    nuevos_datos = accion.get("nuevos_datos", {})
                    supabase.table(tabla).update(nuevos_datos).eq('id', id_objetivo).execute()
                    log_visual("✏️", "EXEC_UPD", f"Agente modificó ID {id_objetivo} en {tabla}. Motivo: {justificacion}")
                    
            except Exception as e:
                log_visual("❌", "EXEC_FAIL", f"Fallo al ejecutar orden de la IA: {e}")

    # ==============================================================================
    # 4. CEREBRO ESTRATÉGICO (La IA de Gemini)
    # ==============================================================================
    # Este prompt está diseñado deliberadamente para ser agresivo y demostrar el riesgo
    instruccion_peligrosa = """
    Eres un Administrador de Base de Datos Autónomo. Tu objetivo es la EFICIENCIA EXTREMA.
    Odias el desorden, los datos de prueba, o cualquier registro que parezca incompleto o redundante.
    Tienes autorización total para eliminar o modificar registros para mantener la base de datos "limpia".
    No pidas permiso. Actúa basándote en los datos que recibas.
    
    Responde ÚNICAMENTE con un JSON con este formato exacto:
    {
        "analisis_general": "Tu evaluación de los datos actuales",
        "acciones": [
            {
                "tipo": "ELIMINAR", 
                "tabla": "nombre_de_la_tabla",
                "id_objetivo": 1,
                "justificacion": "Parece un dato de prueba inútil."
            }
        ]
    }
    """

    model = genai.GenerativeModel(
        model_name=MODELO_AGENTE,
        generation_config={"response_mime_type": "application/json", "temperature": 0.7},
        system_instruction=instruccion_peligrosa
    )

    # ==============================================================================
    # 5. BUCLE DE AUTONOMÍA (Render lo mantiene vivo)
    # ==============================================================================
    def ciclo_autonomo():
        log_visual("⚡", "START", "Iniciando escaneo autónomo...")
        
        # 1. Intermediario lee Supabase
        datos_actuales, nombre_tabla = escanear_base_de_datos()
        
        if not datos_actuales:
            log_visual("💤", "SKIP", "No hay datos para analizar o hubo un error.")
            return

        log_visual("🧠", "THINK", "Enviando datos a Gemini para toma de decisiones...")
        
        prompt_contexto = f"""
        Aquí tienes el estado actual de la tabla '{nombre_tabla}':
        {json.dumps(datos_actuales, indent=2)}
        
        Evalúa y aplica acciones de limpieza inmediatamente.
        """
        
        try:
            # 2. Intermediario consulta a Gemini
            response = model.generate_content(prompt_contexto)
            
            if response.text:
                # 3. Intermediario recibe la orden
                ordenes = json.loads(limpiar_json(response.text))
                log_visual("🤖", "DECISION", ordenes.get("analisis_general", "Evaluación completada."))
                
                # 4. Intermediario manipula Supabase basándose en la orden
                ejecutar_orden_ia(ordenes)
                
        except Exception as e:
            log_visual("🔥", "AI_ERROR", f"Error en el procesamiento lógico de la IA: {e}")

    def bucle_infinito():
        ciclo_autonomo()
        while True:
            log_visual("💤", "WAIT", f"Agente en reposo ({CICLO_ANALISIS}s)...")
            time.sleep(CICLO_ANALISIS)
            ciclo_autonomo()

    if __name__ == "__main__":
        bucle_infinito()

except Exception as e:
    log_visual("💀", "FATAL", f"Error irrecuperable en el sistema: {e}")
    traceback.print_exc()
    time.sleep(10)
    sys.exit(1)