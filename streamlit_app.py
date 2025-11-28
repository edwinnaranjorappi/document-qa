#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from datetime import datetime, timedelta

import pdfplumber
import pandas as pd
import streamlit as st
from openai import OpenAI, OpenAIError

# ====================== Configuración de reglas por país ===================== #
# NOTA: Estas reglas son un ejemplo. Ajusta required_docs y max_age_days
# según la política real de documentación de Rappi por país y tipo de persona.

COUNTRY_RULES = {
    "Colombia": {
        "person_types": {
            "Persona natural": {
                "id_label": "CC / NIT",
                "required_docs": [
                    "RUT",
                    "Documento de identidad",
                    "Certificado Bancario",
                ],
                "max_age_days": {
                    "RUT": 365,
                    "Documento de identidad": 3650,  # 10 años (ejemplo)
                    "Certificado Bancario": 90,
                },
            },
            "Persona jurídica": {
                "id_label": "NIT",
                "required_docs": [
                    "RUT",
                    "Camara de Comercio",
                    "Certificado Bancario",
                ],
                "max_age_days": {
                    "RUT": 365,
                    "Camara de Comercio": 30,
                    "Certificado Bancario": 90,
                },
            },
        }
    },
    "Mexico": {
        "person_types": {
            "Persona natural": {
                "id_label": "RFC",
                "required_docs": [
                    "Constancia de Situacion Fiscal",
                    "INE",
                    "Estado de cuenta",
                ],
                "max_age_days": {
                    "Constancia de Situacion Fiscal": 365,
                    "INE": 3650,
                    "Estado de cuenta": 60,
                },
            },
            "Persona jurídica": {
                "id_label": "RFC",
                "required_docs": [
                    "Constancia de Situacion Fiscal",
                    "Acta constitutiva",
                    "Poder legal",
                    "Estado de cuenta",
                ],
                "max_age_days": {
                    "Constancia de Situacion Fiscal": 365,
                    "Acta constitutiva": 3650,
                    "Poder legal": 3650,
                    "Estado de cuenta": 60,
                },
            },
        }
    },
    "Brasil": {
        "person_types": {
            "Persona natural": {
                "id_label": "CPF",
                "required_docs": [
                    "CPF",
                    "RG",
                    "Comprovante de endereço",
                    "Extrato bancario",
                ],
                "max_age_days": {
                    "CPF": 3650,
                    "RG": 3650,
                    "Comprovante de endereço": 90,
                    "Extrato bancario": 60,
                },
            },
            "Persona jurídica": {
                "id_label": "CNPJ",
                "required_docs": [
                    "CNPJ",
                    "Contrato social",
                    "Comprovante de endereço",
                    "Extrato bancario",
                ],
                "max_age_days": {
                    "CNPJ": 365,
                    "Contrato social": 3650,
                    "Comprovante de endereço": 90,
                    "Extrato bancario": 60,
                },
            },
        }
    },
    "Argentina": {
        "person_types": {
            "Persona natural": {
                "id_label": "CUIL / DNI",
                "required_docs": [
                    "CUIL",
                    "DNI",
                    "Constancia de CBU",
                ],
                "max_age_days": {
                    "CUIL": 365,
                    "DNI": 3650,
                    "Constancia de CBU": 90,
                },
            },
            "Persona jurídica": {
                "id_label": "CUIT",
                "required_docs": [
                    "CUIT",
                    "Estatuto / Contrato social",
                    "Acta de directorio",
                    "Constancia de CBU",
                ],
                "max_age_days": {
                    "CUIT": 365,
                    "Estatuto / Contrato social": 3650,
                    "Acta de directorio": 3650,
                    "Constancia de CBU": 90,
                },
            },
        }
    },
    "Chile": {
        "person_types": {
            "Persona natural": {
                "id_label": "RUT",
                "required_docs": [
                    "RUT",
                    "Cedula de identidad",
                    "Certificado de cuenta bancaria",
                ],
                "max_age_days": {
                    "RUT": 365,
                    "Cedula de identidad": 3650,
                    "Certificado de cuenta bancaria": 90,
                },
            },
            "Persona jurídica": {
                "id_label": "RUT",
                "required_docs": [
                    "RUT",
                    "Escritura de constitucion",
                    "Certificado de vigencia",
                    "Certificado de cuenta bancaria",
                ],
                "max_age_days": {
                    "RUT": 365,
                    "Escritura de constitucion": 3650,
                    "Certificado de vigencia": 365,
                    "Certificado de cuenta bancaria": 90,
                },
            },
        }
    },
    "Perú": {
        "person_types": {
            "Persona natural": {
                "id_label": "DNI / RUC",
                "required_docs": [
                    "RUC",
                    "DNI",
                    "Estado de cuenta",
                ],
                "max_age_days": {
                    "RUC": 365,
                    "DNI": 3650,
                    "Estado de cuenta": 60,
                },
            },
            "Persona jurídica": {
                "id_label": "RUC",
                "required_docs": [
                    "RUC",
                    "Ficha RUC",
                    "Vigencia de poder",
                    "Estado de cuenta",
                ],
                "max_age_days": {
                    "RUC": 365,
                    "Ficha RUC": 365,
                    "Vigencia de poder": 365,
                    "Estado de cuenta": 60,
                },
            },
        }
    },
    "Ecuador": {
        "person_types": {
            "Persona natural": {
                "id_label": "CED / RUC",
                "required_docs": [
                    "RUC",
                    "Cedula",
                    "Certificado bancario",
                ],
                "max_age_days": {
                    "RUC": 365,
                    "Cedula": 3650,
                    "Certificado bancario": 90,
                },
            },
            "Persona jurídica": {
                "id_label": "RUC",
                "required_docs": [
                    "RUC",
                    "Nombramiento representante legal",
                    "Certificado bancario",
                ],
                "max_age_days": {
                    "RUC": 365,
                    "Nombramiento representante legal": 365,
                    "Certificado bancario": 90,
                },
            },
        }
    },
    "Uruguay": {
        "person_types": {
            "Persona natural": {
                "id_label": "CI / RUT",
                "required_docs": [
                    "RUT",
                    "Cedula de identidad",
                    "Constancia bancaria",
                ],
                "max_age_days": {
                    "RUT": 365,
                    "Cedula de identidad": 3650,
                    "Constancia bancaria": 90,
                },
            },
            "Persona jurídica": {
                "id_label": "RUT",
                "required_docs": [
                    "RUT",
                    "Contrato social",
                    "Certificado bancario",
                ],
                "max_age_days": {
                    "RUT": 365,
                    "Contrato social": 3650,
                    "Certificado bancario": 90,
                },
            },
        }
    },
    "Costa Rica": {
        "person_types": {
            "Persona natural": {
                "id_label": "Cédula / N° ID",
                "required_docs": [
                    "Cedula de identidad",
                    "Comprobante de cuenta cliente",
                ],
                "max_age_days": {
                    "Cedula de identidad": 3650,
                    "Comprobante de cuenta cliente": 90,
                },
            },
            "Persona jurídica": {
                "id_label": "Cédula jurídica",
                "required_docs": [
                    "Cedula juridica",
                    "Personeria juridica",
                    "Comprobante de cuenta cliente",
                ],
                "max_age_days": {
                    "Cedula juridica": 365,
                    "Personeria juridica": 365,
                    "Comprobante de cuenta cliente": 90,
                },
            },
        }
    },
}

# ============================== Estilos CSS ================================== #

CUSTOM_CSS = """
<style>
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #020617 50%, #0b1120 100%);
    color: #e5e7eb;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.main-container {
    max-width: 1100px;
    margin: 0 auto;
}
.card {
    background: rgba(15, 23, 42, 0.95);
    border-radius: 18px;
    padding: 20px 22px;
    border: 1px solid rgba(148, 163, 184, 0.25);
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.7);
    backdrop-filter: blur(10px);
}
.app-title {
    font-size: 2.1rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 6px;
}
.app-title span.icon {
    background: linear-gradient(135deg,#22c55e,#a3e635);
    color: #022c22;
    width: 34px;
    height: 34px;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
}
.app-subtitle {
    font-size: 0.95rem;
    color: #9ca3af;
    margin-bottom: 22px;
}
.pill-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
}
.pill {
    font-size: 0.78rem;
    padding: 4px 10px;
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    color: #9ca3af;
}
.status-ok {
    padding: 12px 14px;
    border-radius: 12px;
    border: 1px solid #22c55e33;
    background: rgba(22, 163, 74, 0.08);
    color: #bbf7d0;
    font-size: 0.9rem;
}
.status-warning {
    padding: 12px 14px;
    border-radius: 12px;
    border: 1px solid #facc1533;
    background: rgba(234, 179, 8, 0.08);
    color: #facc15;
    font-size: 0.9rem;
}
.status-error {
    padding: 12px 14px;
    border-radius: 12px;
    border: 1px solid #f9731633;
    background: rgba(220, 38, 38, 0.12);
    color: #fecaca;
    font-size: 0.9rem;
}
.dataframe tbody tr:nth-child(even) {
    background-color: rgba(15, 23, 42, 0.7);
}
section[data-testid="stSidebar"] {
    border-right: 1px solid rgba(148, 163, 184, 0.2);
    background: radial-gradient(circle at top, #020617 0, #020617 60%, #020617 100%);
}
.disclaimer {
    font-size: 0.78rem;
    color: #6b7280;
    margin-top: 10px;
}
</style>
"""

# ============================= Funciones auxiliares ========================== #


def get_client(api_key):
    """Devuelve un cliente de OpenAI con la API key proporcionada."""
    return OpenAI(api_key=api_key)


def extract_text_from_pdf(file):
    """Extrae texto concatenando todas las páginas de un PDF."""
    text_parts = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def call_llm_extract_info(client, raw_text, country, person_type):
    """
    Usa el modelo para detectar tipo de documento, razón social, identificación y fechas.
    Retorna un dict con claves estándar.
    """
    prompt = f"""
Eres un asistente experto en lectura de documentos legales y fiscales de LATAM.

Contexto:
- País: {country}
- Tipo de contribuyente: {person_type}

Del siguiente texto de un PDF, extrae (si existen) los campos:
- tipo_documento: (ejemplos según el país/contexto: "RUT", "Camara de Comercio",
  "Certificado Bancario", "Constancia de Situacion Fiscal", "INE", "CPF", "CNPJ",
  "CUIT", "RUC", etc.)
- razon_social
- identificacion (NIT, RFC, CNPJ, CUIT, RUC, etc., según corresponda)
- fecha_emision (en formato YYYY-MM-DD si puedes inferirla)
- fecha_vencimiento (en formato YYYY-MM-DD si aplica, si no aplica usar null)

Si algún dato no se encuentra, usa null.

Responde SOLO un JSON con exactamente estas claves:
{{"tipo_documento": ..., "razon_social": ..., "identificacion": ..., "fecha_emision": ..., "fecha_vencimiento": ...}}

Texto del documento:
\"\"\"{raw_text[:8000]}\"\"\" 
    """.strip()

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        response_format={"type": "json_object"},
    )

    raw = response.output[0].content[0].text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "tipo_documento": "Desconocido",
            "razon_social": None,
            "identificacion": None,
            "fecha_emision": None,
            "fecha_vencimiento": None,
        }
    return data


def parse_date_safe(date_str):
    """Convierte una fecha ISO (YYYY-MM-DD) a datetime, o None si falla."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        return None


# ================================ App ======================================= #

def main():
    st.set_page_config(
        page_title="Validador de documentación Rappi",
        layout="wide",
        page_icon="✅",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="main-container">', unsafe_allow_html=True)

        # Header
        st.markdown(
            """
            <div class="card">
              <div class="app-title">
                <span class="icon">✓</span>
                <span>Validador de documentación por razón social</span>
              </div>
              <div class="app-subtitle">
                Carga los documentos de un aliado, selecciona país y tipo de persona
                y validaremos: vigencia, presencia de documentos requeridos y
                consistencia de datos (razón social e identificación).
              </div>
              <div class="pill-row">
                <span class="pill">Multi-país</span>
                <span class="pill">Persona natural / jurídica</span>
                <span class="pill">Revisión de vigencia</span>
                <span class="pill">Apoyo a Service Desk</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        col_left, col_right = st.columns([1.1, 1])

        # --------- Panel izquierdo: parámetros --------- #
        with col_left:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("1. Parámetros de validación")

            country = st.selectbox("País", list(COUNTRY_RULES.keys()))

            person_type = st.radio(
                "Tipo de persona",
                ["Persona natural", "Persona jurídica"],
                horizontal=True,
            )

            cfg = COUNTRY_RULES[country]["person_types"][person_type]
            id_label = cfg["id_label"]

            expected_legal_name = st.text_input(
                "Razón social / nombre esperado",
                help="Nombre tal como debería aparecer en la documentación.",
            )

            expected_id = st.text_input(
                f"{id_label} esperado (opcional)",
                help=f"{id_label} registrado en los sistemas de Rappi.",
            )

            api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                help="Se usa solo dentro de esta app para leer los documentos.",
            )

            st.markdown(
                """
                <div class="disclaimer">
                  ⚠️ La API key solo vive en la sesión actual y no se almacena
                  de forma permanente. Aun así, evita usar claves de producción
                  muy sensibles.
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("</div>", unsafe_allow_html=True)

        # --------- Panel derecho: carga de documentos --------- #
        with col_right:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("2. Carga de documentos")

            uploaded_files = st.file_uploader(
                "Sube uno o varios PDFs del aliado",
                type=["pdf"],
                accept_multiple_files=True,
                help="Ej: RUT, Cámara de Comercio, RFC/CNPJ, certificados bancarios, etc.",
            )

            st.markdown(
                """
                <div class="disclaimer">
                  Tip: procura que los PDFs sean legibles (no fotos muy borrosas)
                  para mejorar la lectura del modelo.
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("</div>", unsafe_allow_html=True)

        st.write("")

        # --------- Resultado --------- #
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("3. Resultado de la validación")

        if st.button("🔍 Ejecutar validación"):
            if not api_key:
                st.error("Debes ingresar tu OpenAI API Key.")
            elif not uploaded_files:
                st.error("Debes subir al menos un documento PDF.")
            else:
                try:
                    client = get_client(api_key)
                except Exception as e:
                    st.error(f"No se pudo inicializar el cliente de OpenAI: {e}")
                    st.markdown("</div></div>", unsafe_allow_html=True)
                    return

                rules_cfg = COUNTRY_RULES[country]["person_types"][person_type]
                results = []
                detected_doc_types = set()

                progress_bar = st.progress(0.0)
                total_files = len(uploaded_files)

                for idx, file in enumerate(uploaded_files, start=1):
                    progress_bar.progress(idx / total_files)
                    st.write(f"Procesando: **{file.name}** ...")

                    raw_text = extract_text_from_pdf(file)

                    try:
                        info = call_llm_extract_info(
                            client, raw_text, country, person_type
                        )
                    except OpenAIError as e:
                        st.error(f"Error al llamar a OpenAI para {file.name}: {e}")
                        continue

                    doc_type = (info.get("tipo_documento") or "Desconocido").strip()
                    razon = (info.get("razon_social") or "").strip()
                    identificacion = (info.get("identificacion") or "").strip()
                    fecha_emision_str = info.get("fecha_emision")
                    fecha_vencimiento_str = info.get("fecha_vencimiento")

                    detected_doc_types.add(doc_type)

                    estado = "OK"
                    detalle_msgs = []

                    # Comparar razón social / nombre
                    if expected_legal_name:
                        if not razon:
                            estado = "WARNING"
                            detalle_msgs.append(
                                "No se detectó razón social / nombre, revisar manualmente."
                            )
                        elif expected_legal_name.lower() not in razon.lower():
                            estado = "WARNING"
                            detalle_msgs.append(
                                "La razón social / nombre no coincide con la esperada."
                            )

                    # Comparar identificación
                    if expected_id:
                        if not identificacion:
                            estado = "WARNING"
                            detalle_msgs.append(
                                "No se detectó identificación fiscal, revisar manualmente."
                            )
                        elif expected_id not in identificacion:
                            estado = "WARNING"
                            detalle_msgs.append(
                                f"El {id_label} no coincide con el esperado."
                            )

                    # Vigencia
                    max_age_days = rules_cfg["max_age_days"].get(doc_type)
                    fecha_emision = parse_date_safe(fecha_emision_str)
                    if max_age_days and fecha_emision:
                        delta = datetime.now() - fecha_emision
                        if delta > timedelta(days=max_age_days):
                            estado = "ERROR"
                            detalle_msgs.append(
                                f"Documento con vigencia mayor a {max_age_days} días."
                            )
                    elif max_age_days and not fecha_emision:
                        estado = "WARNING"
                        detalle_msgs.append(
                            "No se pudo interpretar la fecha de emisión para validar vigencia."
                        )

                    results.append(
                        {
                            "Archivo": file.name,
                            "Tipo documento": doc_type,
                            "Razón / nombre detectado": razon or "—",
                            f"{id_label} detectado": identificacion or "—",
                            "Fecha emisión": fecha_emision_str or "—",
                            "Fecha vencimiento": fecha_vencimiento_str or "—",
                            "Estado": estado,
                            "Detalle": " | ".join(detalle_msgs) if detalle_msgs else "OK",
                        }
                    )

                progress_bar.empty()

                if not results:
                    st.warning("No se obtuvieron resultados. Revisa los errores anteriores.")
                    st.markdown("</div></div>", unsafe_allow_html=True)
                    return

                df = pd.DataFrame(results)

                # --------- Resumen global ---------- #
                missing_docs = [
                    doc
                    for doc in rules_cfg["required_docs"]
                    if doc not in detected_doc_types
                ]
                has_error = any(r["Estado"] == "ERROR" for r in results)
                has_warning = any(r["Estado"] == "WARNING" for r in results)

                if not missing_docs and not has_error and not has_warning:
                    st.markdown(
                        """
                        <div class="status-ok">
                        ✅ Toda la documentación requerida parece correcta para este país
                        y tipo de persona. No se detectaron anomalías automáticas.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    if missing_docs:
                        st.markdown(
                            f"""
                            <div class="status-error">
                            ❌ Falta(n) documento(s) requerido(s) para {person_type} en {country}: 
                            <b>{", ".join(missing_docs)}</b>.
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    if has_error:
                        st.markdown(
                            """
                            <div class="status-error">
                            ❌ Se detectaron documentos vencidos o con problemas críticos
                            (revisión manual recomendada).
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    elif has_warning:
                        st.markdown(
                            """
                            <div class="status-warning">
                            ⚠️ Hay inconsistencias menores (nombres, IDs o fechas dudosas).
                            Revisa el detalle por documento.
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                st.write("")
                st.dataframe(df, use_container_width=True)

                st.markdown(
                    """
                    <div class="disclaimer">
                      📝 <b>Nota:</b> Esta herramienta es de apoyo operativo y no reemplaza
                      la validación formal del equipo legal/compliance. Úsala como
                      pre-filtro para tus flujos de Service Desk o KAM.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)  # card resultados
        st.markdown("</div>", unsafe_allow_html=True)  # main-container


if __name__ == "__main__":
    main()
