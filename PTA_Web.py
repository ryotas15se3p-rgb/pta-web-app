import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

# --- 🔐 セキュリティ設定 ---
ADMIN_ID = "admin"
ADMIN_PASS = "pta700"
DB_FILE = "PTA_database.db"

st.set_page_config(page_title="PTAクラウド支部", layout="centered")

# --- 認証機能 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 PTAクラウド支部 ログイン")
        u = st.text_input("ユーザーID")
        p = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if u == ADMIN_ID and p == ADMIN_PASS:
                st.session_state["password_correct"] = True
                st.session_state["current_user_id"] = u
                st.rerun()
            else: st.error("IDかパスワードが違います。")
        return False
    return True

# --- データベース機能 ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_type TEXT, user TEXT, date TEXT, time TEXT, event TEXT,
        location TEXT, dress TEXT, person TEXT, participants TEXT, caution TEXT
    )''')
    conn.commit(); conn.close()

# --- オートセーブの裏方関数 ---
def auto_save():
    # IDがある時は更新、ない時は新規作成するロジック
    # 注意: Streamlitの複雑な挙動を避けるため、今回は「入力するたびに保存」というより
    # 「保存ボタン」の信頼性を高める実装に切り替えます
    pass

# --- PDF生成 ---
def generate_pdf(data):
    filepath = "PTA_Output.pdf"
    c = canvas.Canvas(filepath, pagesize=A4)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, "msgothic.ttc")
    font_name = "MS-Gothic-Web"
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            f_main = font_name
        except: f_main = "Helvetica"
    else: f_main = "Helvetica"
    
    def draw_header(canvas_obj, page_num):
        canvas_obj.setFont(f_main, 18)
        canvas_obj.drawCentredString(105*mm, 280*mm, f"PTA {data['doc_type']} ({page_num}ページ)")
        canvas_obj.line(20*mm, 275*mm, 190*mm, 275*mm)

    page_count = 1; draw_header(c, page_count)
    y = 265
    items = [("担当者", data['user']), ("日付", data['date']), ("時間", data['time']), 
             ("行事名", data['event']), ("場所", data['location']), ("服装", data['dress']), 
             ("同行者", data['person']), ("参加人数", data['participants'])]
    for label, val in items:
        if val:
            c.setFont(f_main, 11)
            c.drawString(25*mm, y*mm, f"【{label}】: {val}")
            y -= 10
            
    c.drawString(25*mm, y*mm, "【内容・注意事項】:")
    c.setFont(f_main, 10)
    y -= 8
    
    caution_text = data['caution'] if data['caution'] else ""
    for raw_line in caution_text.splitlines():
        for i in range(0, len(raw_line), 35):
            if y < 20: 
                c.showPage(); page_count += 1; draw_header(c, page_count); y = 265
            c.drawString(30*mm, y*mm, raw_line[i:i+35]); y -= 6
    c.showPage(); c.save()
    return filepath

# --- メイン画面 ---
if check_password():
    init_db()
    if st.sidebar.button("ログアウト"): st.session_state.clear(); st.rerun()

    st.title("📱 PTAクラウド支部 Ver.3.8")
    tab1, tab2 = st.tabs(["📝 新規入力・編集", "📚 履歴・管理"])

    # ID保持用
    if 'edit_id' not in st.session_state: st.session_state.edit_id = None

    with tab2:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM notes ORDER BY id DESC", conn)
        conn.close()
        if not df.empty:
            event_options = {f"ID:{r['id']} - {r['event']}": r['id'] for _, r in df.iterrows()}
            selected_key = st.selectbox("データを選択", list(event_options.keys()), index=None)
            if selected_key:
                target_id = event_options[selected_key]
                if st.button("🔧 編集読み込み"): st.session_state.edit_id = target_id; st.success("読み込みました！")
            st.dataframe(df[['id', 'date', 'event', 'user']], use_container_width=True, hide_index=True)
        
    with tab1:
        is_edit = st.session_state.edit_id is not None
        # データ取得
        if is_edit:
            conn = sqlite3.connect(DB_FILE)
            cur_data = pd.read_sql_query(f"SELECT * FROM notes WHERE id={st.session_state.edit_id}", conn).iloc[0]
            conn.close()
            if st.button("❌ 編集キャンセル"): st.session_state.edit_id = None; st.rerun()
        else:
            cur_data = None

        with st.form("main_form"):
            doc_type = st.selectbox("書類種別", ["議事録", "備忘録"], index=0 if not is_edit else (0 if cur_data['doc_type']=="議事録" else 1))
            user = st.selectbox("担当者", ["小此木", "澤田", "寺山"], index=0)
            date = st.date_input("日付", datetime.now())
            event = st.text_input("行事名・件名", value=cur_data['event'] if is_edit else "")
            c_l, c_r = st.columns(2)
            with c_l:
                time = st.text_input("時間", value=cur_data['time'] if is_edit else "")
                location = st.text_input("場所", value=cur_data['location'] if is_edit else "")
            with c_r:
                dress = st.text_input("服装", value=cur_data['dress'] if is_edit else "")
                person = st.text_input("同行者", value=cur_data['person'] if is_edit else "")
            participants = st.text_input("参加人数", value=cur_data['participants'] if is_edit else "")
            caution = st.text_area("内容・注意事項", height=200, value=cur_data['caution'] if is_edit else "")
            
            # 【重要】フォームを使ってまとめて保存することで、途中のミスを防ぐ
            submitted = st.form_submit_button("💾 保存する")
            if submitted:
                conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
                v = (doc_type, user, date.strftime('%Y/%m/%d'), time, event, location, dress, person, participants, caution)
                if is_edit: cur.execute("UPDATE notes SET doc_type=?, user=?, date=?, time=?, event=?, location=?, dress=?, person=?, participants=?, caution=? WHERE id=?", v + (st.session_state.edit_id,))
                else: cur.execute("INSERT INTO notes (doc_type, user, date, time, event, location, dress, person, participants, caution) VALUES (?,?,?,?,?,?,?,?,?,?)", v)
                conn.commit(); conn.close(); st.success("保存完了！これで安心だぜ。")

        # PDFボタンはフォーム外で
        if st.button("📄 PDFを作成する"):
             d = {"doc_type": doc_type, "user": user, "date": date.strftime('%Y/%m/%d'), "time": time, "event": event, "location": location, "dress": dress, "person": person, "participants": participants, "caution": caution}
             pdf_path = generate_pdf(d)
             with open(pdf_path, "rb") as f:
                 st.download_button("📥 PDFをダウンロード", f, file_name=f"PTA_{event}.pdf")
