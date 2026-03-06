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

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_type TEXT, user TEXT, date TEXT, time TEXT, event TEXT,
        location TEXT, dress TEXT, person TEXT, participants TEXT, caution TEXT
    )''')
    conn.commit(); conn.close()

# --- 共通保存処理（ここがキモ！） ---
def save_data(is_edit, edit_id, data_tuple):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    if is_edit and edit_id:
        cur.execute("UPDATE notes SET doc_type=?, user=?, date=?, time=?, event=?, location=?, dress=?, person=?, participants=?, caution=? WHERE id=?", data_tuple + (edit_id,))
    else:
        cur.execute("INSERT INTO notes (doc_type, user, date, time, event, location, dress, person, participants, caution) VALUES (?,?,?,?,?,?,?,?,?,?)", data_tuple)
    conn.commit()
    # 新規保存の場合、新しく発行されたIDを返す
    new_id = cur.lastrowid if not is_edit else edit_id
    conn.close()
    return new_id

# --- PDF生成（Ver.3.5の改ページ版を継承） ---
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
            c.setFont(f_main, 11); c.drawString(25*mm, y*mm, f"【{label}】: {val}"); y -= 10
            
    c.drawString(25*mm, y*mm, "【内容・注意事項】:")
    c.setFont(f_main, 10); y -= 8
    
    caution_text = data['caution'] if data['caution'] else ""
    for raw_line in caution_text.splitlines():
        for i in range(0, len(raw_line), 35):
            if y < 20: 
                c.showPage(); page_count += 1; draw_header(c, page_count); y = 265; c.setFont(f_main, 10)
            c.drawString(30*mm, y*mm, raw_line[i:i+35]); y -= 6
    c.showPage(); c.save()
    return filepath

# --- メイン画面 ---
if check_password():
    init_db()
    if st.sidebar.button("ログアウト"): st.session_state.clear(); st.rerun()

    st.title("📱 PTAクラウド支部 Ver.3.9")
    tab1, tab2 = st.tabs(["📝 入力・編集", "📚 履歴・管理"])

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
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("🔧 編集読み込み", use_container_width=True):
                        st.session_state.edit_id = target_id; st.success("読み込み完了！"); st.rerun()
                with col_b:
                    if st.button("🗑️ データを抹消", type="primary", use_container_width=True):
                        conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
                        cur.execute(f"DELETE FROM notes WHERE id={target_id}")
                        conn.commit(); conn.close(); st.rerun()
            st.divider()
            st.dataframe(df[['id', 'date', 'event', 'user']], use_container_width=True, hide_index=True)
        
    with tab1:
        is_edit = st.session_state.edit_id is not None
        if is_edit:
            st.info(f"💡 ID:{st.session_state.edit_id} を編集中")
            conn = sqlite3.connect(DB_FILE)
            cur_data = pd.read_sql_query(f"SELECT * FROM notes WHERE id={st.session_state.edit_id}", conn).iloc[0]
            conn.close()
            if st.button("❌ 編集キャンセル"): st.session_state.edit_id = None; st.rerun()
        
        # 入力フォーム
        doc_type = st.selectbox("書類", ["議事録", "備忘録"], index=0 if not is_edit else (0 if cur_data['doc_type']=="議事録" else 1))
        user_list = ["小此木", "澤田", "寺山"]
        user = st.selectbox("担当", user_list, index=user_list.index(cur_data['user']) if is_edit and cur_data['user'] in user_list else 0)
        date = st.date_input("日付", datetime.strptime(cur_data['date'], '%Y/%m/%d') if is_edit else datetime.now())
        event = st.text_input("行事名", value=cur_data['event'] if is_edit else "")
        c_l, c_r = st.columns(2)
        with c_l:
            time = st.text_input("時間", value=cur_data['time'] if is_edit else "")
            location = st.text_input("場所", value=cur_data['location'] if is_edit else "")
        with c_r:
            dress = st.text_input("服装", value=cur_data['dress'] if is_edit else "")
            person = st.text_input("同行者", value=cur_data['person'] if is_edit else "")
        participants = st.text_input("参加人数", value=cur_data['participants'] if is_edit else "")
        caution = st.text_area("内容", height=200, value=cur_data['caution'] if is_edit else "")

        st.divider()
        col1, col2 = st.columns(2)
        
        v = (doc_type, user, date.strftime('%Y/%m/%d'), time, event, location, dress, person, participants, caution)

        with col1:
            if st.button("💾 保存のみ", use_container_width=True):
                if event:
                    st.session_state.edit_id = save_data(is_edit, st.session_state.edit_id, v)
                    st.success("保存完了だぜ！")
                else: st.error("行事名を入れてくれ。")

        with col2:
            # PDF準備ボタンを押したとき、同時に保存も走らせる！
            if st.button("📄 PDF作成＆保存", use_container_width=True):
                if event:
                    # まず保存
                    st.session_state.edit_id = save_data(is_edit, st.session_state.edit_id, v)
                    # 次にPDF作成
                    d = {"doc_type": doc_type, "user": user, "date": date.strftime('%Y/%m/%d'), "time": time, "event": event, "location": location, "dress": dress, "person": person, "participants": participants, "caution": caution}
                    pdf_path = generate_pdf(d)
                    with open(pdf_path, "rb") as f:
                        st.download_button("📥 PDFをダウンロード", f, file_name=f"PTA_{event}.pdf", use_container_width=True)
                    st.success("データベースに保存してからPDFを作ったぜ！")
                else: st.error("行事名がないと保存できないぜ。")
