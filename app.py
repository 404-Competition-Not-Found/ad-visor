import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
import json
import pandas as pd
import altair as alt 


# Carica le variabili d'ambiente dal file .env
load_dotenv()

# --- Configurazione Iniziale ---
st.set_page_config(
    page_title="Ad-Visor",
    page_icon="📹",
    layout="wide"
)

# Configura la chiave API di Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    st.error("Chiave API di Gemini non trovata. Assicurati di averla impostata nel file .env")
    st.stop()


def main():
    """
    Funzione principale per l'applicazione Ad-Visor.
    """
    # --- Sidebar ---
    with st.sidebar:
        st.title("Ad-Visor")
        st.markdown("---")
        scelta_tool = st.radio(
            "Seleziona uno strumento:",
            ("Video Checker", "Report Hub (Disabilitato)")
        )

        st.markdown("---")
        st.info("Ad-Visor è il tuo assistente AI per l'analisi pre-lancio di contenuti video pubblicitari.")

    # --- Pagina Principale ---
    st.title("📹 Ad-Visor: Analisi Video con AI")

    if scelta_tool == "Video Checker":
        video_checker_tool()
    elif scelta_tool == "Report Hub (Disabilitato)":
        tool_disabilitato()

def video_checker_tool():
    """
    Funzione per lo strumento di analisi video.
    """
    st.header("🔍 Video Checker")
    st.write("Carica un video per analizzare aspetti culturali, DE&I e potenziali problematiche di comunicazione.")

    video_caricato = st.file_uploader("Scegli un file video", type=["mp4", "mov", "avi", "mkv"])


    if video_caricato is not None:
        temp_path = os.path.join("analytics", video_caricato.name)
        with open(temp_path, "wb") as f:
            f.write(video_caricato.getbuffer())
        st.session_state.video_path = temp_path
        st.video(video_caricato)
        
        if st.button("Analizza il Video"):
            with st.spinner("Analisi in corso... Questo processo potrebbe richiedere alcuni minuti."):
                try:
                    # Salva temporaneamente il file
                    with open(video_caricato.name, "wb") as f:
                        f.write(video_caricato.getbuffer())

                    # Carica il video sull'API di Gemini
                    video_file = genai.upload_file(
                        path=video_caricato.name,
                        display_name="video_da_analizzare"
                    )

                    # Attendi che il file venga processato
                    while video_file.state.name == "PROCESSING":
                        st.write("In attesa che il video venga processato dal sistema...")
                        time.sleep(5)
                        video_file = genai.get_file(video_file.name)

                    if video_file.state.name == "FAILED":
                        st.error(f"Elaborazione del video fallita: {video_file.state}")
                        st.stop()

                    # Prompt per l'analisi
                    prompt = """
                    Sei "Ad-Visor", un consulente esperto di marketing e comunicazione globale.
                    Analizza attentamente questo video pubblicitario e fornisci un report dettagliato basato sui seguenti punti:

                    1.  **Analisi Culturale:** Identifica elementi culturali e valuta la loro potenziale risonanza in diversi mercati internazionali.

                    2.  **Valutazione DE&I (Diversity, Equity & Inclusion):**
                        *   **Rappresentazione:** Autenticità vs stereotipi.
                        *   **Inclusività:** Messaggi inclusivi e rischi di esclusione.

                    3.  **Rilevamento di Rischi e Controversie:**
                        *   **Contenuti Sensibili:** Violenza, linguaggio inappropriato, temi controversi.
                        *   **Messaggi Ambigui:** Possibili interpretazioni negative.

                    4.  **Consigli Strategici:** Suggerimenti chiari e attuabili per migliorare l'efficacia globale e ridurre i rischi.

                    Fornisci una risposta ben strutturata con titoli chiari per ogni sezione.
                    """

                    model = genai.GenerativeModel(model_name="gemini-flash-latest")
                    response = model.generate_content([prompt, video_file], request_options={'timeout': 600})

                    st.success("Analisi completata!")
                    st.markdown("---")
                    st.subheader("Risultati dell'Analisi di Ad-Visor")
                    st.markdown(response.text)

                    # Pulisci i file temporanei
                    # genai.delete_file(video_file.name)
                    os.remove(video_caricato.name)
                    


                except Exception as e:
                    st.error(f"Si è verificato un errore durante l'analisi: {e}")

    
        if "analytics_current" not in st.session_state:
            st.session_state.analytics_current = None
        if "analytics_old" not in st.session_state:
            st.session_state.analytics_old = None

        # STEP 1 – Import current analytics
        if st.button("Importa analytics del video"):
            try:
                with open("analytics/analytics1.json", "r") as f:
                    analytics_json = json.load(f)
                    st.session_state.analytics1 = analytics_json
                df = pd.DataFrame(analytics_json["data"])
                df["date"] = pd.to_datetime(df["date"])
                df["version"] = "Current"
                st.session_state.analytics_current = df
                st.success("✅ Dati correnti importati con successo!")
            except Exception as e:
                st.error(f"Errore nel caricamento dei dati correnti: {e}")

        # STEP 2 – Import old analytics (solo dopo aver importato i correnti)
        if st.session_state.analytics_current is not None:
            if st.button("Importa analytics versioni precedenti"):
                try:
                    with open("analytics/analytics2.json", "r") as f:
                        analytics_json = json.load(f)
                        st.session_state.analytics2 = analytics_json

                    df_old = pd.DataFrame(analytics_json["data"])
                    df_old["date"] = pd.to_datetime(df_old["date"])
                    df_old["version"] = "Old"
                    st.session_state.analytics_old = df_old
                    st.success("📉 Dati vecchi importati con successo!")
                except Exception as e:
                    st.error(f"Errore nel caricamento dei dati vecchi: {e}")

        # STEP 3 – Mostra un grafico separato per ogni KPI
        if st.session_state.analytics_current is not None:

            combined_df = st.session_state.analytics_current.copy()
            if st.session_state.analytics_old is not None:
                combined_df = pd.concat([combined_df, st.session_state.analytics_old])

            kpi_columns = ["ROAS", "CPA", "CTR", "CVR", "CPL", "CPC"]

            for kpi in kpi_columns:
                if kpi in combined_df.columns:
                    st.markdown(f"### {kpi}")

                    chart = (
                        alt.Chart(combined_df)
                        .mark_line(point=True)
                        .encode(
                            x=alt.X("date:T", title="Data"),
                            y=alt.Y(f"{kpi}:Q", title=f"Valore {kpi}"),
                            color=alt.Color("version:N", legend=alt.Legend(title="Versione")),
                            tooltip=["date:T", f"{kpi}:Q", "version:N"]
                        )
                        .properties(width=750, height=300)
                    )

                    st.altair_chart(chart, use_container_width=True)

            if st.button("Analizza confronto tra video"):
                if "video_path" not in st.session_state or not os.path.exists(st.session_state.video_path):
                    st.error("⚠️ Carica prima un video da analizzare.")
                    return

                if not os.path.exists("analytics/mock.mp4"):
                    st.error("⚠️ Il file analytics/mock.mp4 non esiste.")
                    return

                with st.spinner("Analisi comparativa in corso..."):
                    try:
                        # Carica entrambi i video su Gemini
                        video_1 = genai.upload_file(path=st.session_state.video_path, display_name="video_corrente")
                        video_2 = genai.upload_file(path="analytics/mock.mp4", display_name="video_mock")

                        # Funzione di utilità: attende che un file diventi ACTIVE
                        def wait_until_active(file_obj):
                            while file_obj.state.name == "PROCESSING":
                                st.write(f"⏳ Attendo che {file_obj.display_name} sia pronta...")
                                time.sleep(3)
                                file_obj = genai.get_file(file_obj.name)
                            if file_obj.state.name != "ACTIVE":
                                raise Exception(f"Il file {file_obj.display_name} non è attivo: {file_obj.state.name}")
                            return file_obj

                        video_1 = wait_until_active(video_1)
                        video_2 = wait_until_active(video_2)

                        model = genai.GenerativeModel(model_name="gemini-flash-latest")

                        # Primo riepilogo: video corrente
                        prompt_summary_v1 = """
                        Sei "Ad-Visor", un consulente senior di marketing e comunicazione.
                        Forni un riassunto dettagliato e strutturato del seguente video pubblicitario, concentrandoti su:
                        1) Tono e ritmo
                        2) Messaggio principale e call-to-action
                        3) Elementi visivi rilevanti (ambientazione, abbigliamento, simboli)
                        4) Rappresentazione e inclusività
                        5) Eventuali elementi potenzialmente rischiosi o controversi
                        6) Un breve paragrafo conclusivo con punti di forza e debolezze
                        Rispondi in formato chiaro con titoli di sezione.
                        """
                        resp_v1 = model.generate_content([prompt_summary_v1, video_1], request_options={'timeout': 600})
                        summary_v1 = resp_v1.text.strip()
                        # st.markdown("### Riassunto Video Corrente")
                        # st.markdown(summary_v1)

                        # Secondo riepilogo: video mock
                        prompt_summary_v2 = """
                        Sei "Ad-Visor", un consulente senior di marketing e comunicazione.
                        Forni un riassunto dettagliato e strutturato del seguente video pubblicitario (versione mock), concentrandoti su:
                        1) Tono e ritmo
                        2) Messaggio principale e call-to-action
                        3) Elementi visivi rilevanti (ambientazione, abbigliamento, simboli)
                        4) Rappresentazione e inclusività
                        5) Eventuali elementi potenzialmente rischiosi o controversi
                        6) Un breve paragrafo conclusivo con punti di forza e debolezze
                        Rispondi in formato chiaro con titoli di sezione.
                        """
                        resp_v2 = model.generate_content([prompt_summary_v2, video_2], request_options={'timeout': 600})
                        summary_v2 = resp_v2.text.strip()
                        # st.markdown("### Riassunto Video Mock")
                        # st.markdown(summary_v2)

                        # Terza chiamata: check sulle differenze, prende i due riassunti testuali
                        prompt_diff = f"""
                        Sei "Ad-Visor", consulente senior.
                        Hai a disposizione due riassunti dettagliati di due video pubblicitari.

                        Riassunto A (Video Corrente):
                        {summary_v1}
                        Con le analytics:
                        {st.session_state.analytics1}

                        Riassunto B (Video Mock):
                        {summary_v2}
                        Con le analytics:
                        {st.session_state.analytics2}

                        Sulla base dei riassunti e dei dati:

                        Spiega in dettaglio perché uno dei due video ha performato meglio dell’altro, considerando:
                        - Tono, ritmo e messaggio
                        - Chiarezza della call-to-action
                        - Elementi visivi e simbolici
                        - Inclusività e rappresentazione
                        - KPI (ROAS, CPA, CTR, CVR, CPL, CPC)
                        
                        Crea una tabella comparativa, in alto le raccomandazioni basandosi sulle differenze
                        """
                        resp_diff = model.generate_content([prompt_diff], request_options={'timeout': 600})
                        st.success("✅ Analisi comparativa completata!")
                        st.subheader("Controllo Differenze e Raccomandazioni")
                        st.markdown(resp_diff.text.strip())

                    except Exception as e:
                        st.error(f"Errore durante l'analisi comparativa: {e}")

                    finally:
                        # Pulisci i file su Gemini (se sono stati caricati)
                        try:
                            if 'video_1' in locals():
                                genai.delete_file(video_1.name)
                            if 'video_2' in locals():
                                genai.delete_file(video_2.name)
                        except Exception:
                            pass
            
                
def tool_disabilitato():
    """
    Funzione per la sezione disabilitata.
    """
    st.header("📊 Report Hub")
    st.warning("Questa funzionalità non è ancora attiva.")
    st.info("Qui potrai visualizzare e gestire i report delle analisi precedenti.")


if __name__ == "__main__":
    main()