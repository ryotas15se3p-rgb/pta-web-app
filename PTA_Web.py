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

# --- 🔐 セキュリティ設定（ここを好きな文字に変えて！） ---
USER_ID = "admin"        # ログインID
USER_PASS = "pta700"     # パスワード

# --- ページ設定 ---
st.set_page_config(page_title="PTAクラウド支部【要認証】", layout="centered")

# --- ログインチェック機能 ---
def check_password():
    """認証が成功したらTrueを返す"""
    def password_entered():
        if st.session_state["username"] == USER_ID and st.session_state["password"] == USER_PASS:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # パスワードをメモリから消す
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 初回表示
        st.title("🔐 PTAクラウド支部 入室管理")
        st.text_input("ID", key="username")
        st.text_input("パスワード", type="password", key="password")
        st.button("ログイン", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        # パスワード間違い
        st.title("🔐 PTAクラウド支部 入室管理")
        st.text_input("ID", key="username")
        st.text_input("パスワード", type="password", key="password")
        st.button("ログイン", on_click=password_entered)
        st.error("IDかパスワードが違うぜ。")
        return False
    else:
        # 認証成功
        return True

# --- データベース初期化 ---
def init_db():
    conn = sqlite3.connect("PTA_database.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_type TEXT, user TEXT, date TEXT, time TEXT, event TEXT,
        location TEXT, dress TEXT, person TEXT, participants TEXT, caution TEXT
    )''')
    conn.commit()
    conn.close()

# --- PDF生成エンジン ---
def generate_pdf(data):
    filepath = "PTA_Output.pdf"
    c = canvas.Canvas(filepath, pagesize=A4)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_file = "msgothic.ttc" 
    font_path = os.path.join(base_dir, font_file)
    font_name = "MS-Gothic-Web"
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            f_main = font_name
        except: f_main = "Helvetica"
    else: f_main = "Helvetica"
    
    c.setFont(f_main, 18)
    c.drawCentredString(105*mm, 280*mm, f"PTA {data['doc_type']}")
    c.line(20*mm, 275*mm, 190*mm, 275*mm)
    c.setFont(f_main, 11)
    y = 265
    items = [("入力者", data['user']), ("開催日", data['date']), ("時間", data['time']), ("行事内容", data['event']), ("開催場所", data['location']), ("服装・持参物", data['dress']), ("同行者", data['person']), ("参加者", data['participants'])]
    for label, val in items:
        if val:
            c.drawString(25*mm, y*mm, f"【{label}】: {val}")
            y -= 10
    c.drawString(25*mm, y*mm, "【内容・注意事項・申し送り】:")
    y -= 8
    t = c.beginText(30*mm, y*mm); t.setFont(f_main, 10); t.setLeading(15)
    caution_text = data['caution'] if data['caution'] else ""
    for line in caution_text.splitlines():
        for i in range(0, len(line), 35): t.textLine(line[i:i+35])
    c.drawText(t); c.showPage(); c.save()
    return filepath

# --- メイン処理 ---
if check_password(): # 認証が通った場合のみ以下を表示
    init_db()
    st.sidebar.write(f"Logged in as: {USER_ID}")
    if st.sidebar.button("ログアウト"):
        st.session_state["password_correct"] = False
        st.rerun()

    st.title("📱 PTAクラウド支部 Ver.3.0")

    if 'edit_id' not in st.session_state:
        st.session_state.edit_id = None

    tab1, tab2 = st.tabs(["📝 入力・編集", "📚 履歴・管理"])

    # (中略：タブの中身はVer.2.1と同じ。スペース節約のため統合して記述)
    with tab2:
        st.subheader("保存済みデータ一覧")
        conn = sqlite3.connect("PTA_database.db")
        df = pd.read_sql_query("SELECT * FROM notes ORDER BY id DESC", conn)
        conn.close()
        if not df.empty:
            event_options = {f"ID:{row['id']} - {row['event']}": row['id'] for _, row in df.iterrows()}
            selected_key = st.selectbox("操作したいデータを選択", list(event_options.keys()), index=None)
            if selected_key:
                target_id = event_options[selected_key]
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("🔧 編集モードで読み込む", use_container_width=True):
                        st.session_state.edit_id = target_id
                        st.success("読み込んだぜ！『入力・編集』タブへ！")
                with col_b:
                    if st.button("🗑️ データを抹消", type="primary", use_container_width=True):
                        conn = sqlite3.connect("PTA_database.db")
                        cursor = conn.cursor()
                        cursor.execute(f"DELETE FROM notes WHERE id={target_id}")
                        conn.commit(); conn.close()
                        st.rerun()
            st.divider()
            st.dataframe(df[['id', 'date', 'event', 'user']], use_container_width=True, hide_index=True)
        else: st.write("データなし。")

    with tab1:
        is_edit = st.session_state.edit_id is not None
        if is_edit:
            st.info(f"💡 ID:{st.session_state.edit_id} を編集中。")
            conn = sqlite3.connect("PTA_database.db")
            cur_data = pd.read_sql_query(f"SELECT * FROM notes WHERE id={st.session_state.edit_id}", conn).iloc[0]
            conn.close()
            if st.button("❌ キャンセル"):
                st.session_state.edit_id = None
                st.rerun()
        
        doc_type = st.selectbox("書類種別", ["議事録", "備忘録"], index=0 if not is_edit else (0 if cur_data['doc_type']=="議事録" else 1))
        user_list = ["小此木", "澤田", "寺山"]
        user = st.selectbox("担当者", user_list, index=user_list.index(cur_data['user']) if is_edit and cur_data['user'] in user_list else 0)
        date = st.date_input("開催日", datetime.strptime(cur_data['date'], '%Y/%m/%d') if is_edit else datetime.now())
        event = st.text_input("行事名", value=cur_data['event'] if is_edit else "")
        caution = st.text_area("内容", height=200, value=cur_data['caution'] if is_edit else "")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🆙 上書き保存" if is_edit else "💾 新規保存", use_container_width=True):
                conn = sqlite3.connect("PTA_database.db")
                cursor = conn.cursor()
                if is_edit:
                    cursor.execute("UPDATE notes SET doc_type=?, user=?, date=?, event=?, caution=? WHERE id=?", (doc_type, user, date.strftime('%Y/%m/%d'), event, caution, st.session_state.edit_id))
                else:
                    cursor.execute("INSERT INTO notes (doc_type, user, date, event, caution) VALUES (?,?,?,?,?)", (doc_type, user, date.strftime('%Y/%m/%d'), event, caution))
                conn.commit(); conn.close()
                st.success("完了だぜ！")
        with col2:
            if st.button("📄 PDF準備", use_container_width=True):
                pdf_path = generate_pdf({"doc_type": doc_type, "user": user, "date": date.strftime('%Y/%m/%d'), "time": "", "event": event, "location": "", "dress": "", "person": "", "participants": "", "caution": caution})
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 PDF保存", f, file_name=f"PTA_{event}.pdf", use_container_width=True)
