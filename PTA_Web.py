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
USER_ID = "admin"        # ログインID
USER_PASS = "pta700"     # パスワード
DB_FILE = "PTA_database.db"

# --- ページ設定 ---
st.set_page_config(page_title="PTAクラウド支部", layout="centered")

# --- ログインチェック ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 PTAクラウド支部 入室管理")
        u = st.text_input("ID")
        p = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if u == USER_ID and p == USER_PASS:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("IDかパスワードが違うぜ。")
        return False
    return True

# --- データベース初期化（全項目対応） ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_type TEXT, user TEXT, date TEXT, time TEXT, event TEXT,
        location TEXT, dress TEXT, person TEXT, participants TEXT, caution TEXT
    )''')
    conn.commit(); conn.close()

# --- PDF生成エンジン（詳細項目も全描画） ---
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
    
    # タイトル
    c.setFont(f_main, 18)
    c.drawCentredString(105*mm, 280*mm, f"PTA {data['doc_type']}")
    c.line(20*mm, 275*mm, 190*mm, 275*mm)
    
    # 項目描画
    c.setFont(f_main, 11)
    y = 265
    items = [
        ("入力者", data['user']), ("開催日", data['date']), ("時間", data['time']), 
        ("行事内容", data['event']), ("開催場所", data['location']), 
        ("服装・持参物", data['dress']), ("同行者", data['person']), 
        ("参加者", data['participants'])
    ]
    
    for label, val in items:
        if val:
            c.drawString(25*mm, y*mm, f"【{label}】: {val}")
            y -= 10
            
    c.drawString(25*mm, y*mm, "【内容・注意事項・申し送り】:")
    y -= 8
    
    # 本文（折り返し）
    t = c.beginText(30*mm, y*mm)
    t.setFont(f_main, 10)
    t.setLeading(15)
    caution_text = data['caution'] if data['caution'] else ""
    for line in caution_text.splitlines():
        for i in range(0, len(line), 35):
            t.textLine(line[i:i+35])
    
    c.drawText(t)
    c.showPage()
    c.save()
    return filepath

# --- メイン処理 ---
if check_password():
    init_db()
    st.sidebar.button("ログアウト", on_click=lambda: st.session_state.clear())

    st.title("📱 PTAクラウド支部 Ver.3.2")
    tab1, tab2 = st.tabs(["📝 入力・編集", "📚 履歴・管理"])

    if 'edit_id' not in st.session_state: st.session_state.edit_id = None

    with tab2:
        st.subheader("保存済みデータ一覧")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM notes ORDER BY id DESC", conn)
        conn.close()
        
        if not df.empty:
            event_options = {f"ID:{r['id']} - {r['event']}": r['id'] for _, r in df.iterrows()}
            selected_key = st.selectbox("データを選択", list(event_options.keys()), index=None, placeholder="編集・削除するデータを選んでくれ")
            
            if selected_key:
                target_id = event_options[selected_key]
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🔧 編集読み込み", use_container_width=True):
                        st.session_state.edit_id = target_id
                        st.success("読み込んだぜ！タブを移動してくれ。")
                with c2:
                    if st.button("🗑️ データを抹消", type="primary", use_container_width=True):
                        conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
                        cur.execute(f"DELETE FROM notes WHERE id={target_id}")
                        conn.commit(); conn.close(); st.rerun()
            st.divider()
            st.dataframe(df[['id', 'date', 'event', 'user']], use_container_width=True, hide_index=True)
            
            with st.expander("🛠 会長専用バックアップ"):
                if os.path.exists(DB_FILE):
                    with open(DB_FILE, "rb") as f:
                        st.download_button("📥 DBファイルをダウンロード", f, file_name=f"PTA_Backup_{datetime.now().strftime('%Y%m%d')}.db", mime="application/octet-stream", use_container_width=True)
        else: st.write("データなし。")

    with tab1:
        is_edit = st.session_state.edit_id is not None
        if is_edit:
            st.info(f"💡 ID:{st.session_state.edit_id} を編集中")
            conn = sqlite3.connect(DB_FILE)
            cur_data = pd.read_sql_query(f"SELECT * FROM notes WHERE id={st.session_state.edit_id}", conn).iloc[0]
            conn.close()
            if st.button("❌ 編集をキャンセル"):
                st.session_state.edit_id = None; st.rerun()
        
        # --- 入力フォーム（ここがフルスペック！） ---
        doc_type = st.selectbox("書類", ["議事録", "備忘録"], index=0 if not is_edit else (0 if cur_data['doc_type']=="議事録" else 1))
        user_list = ["小此木", "澤田", "寺山"]
        user = st.selectbox("担当", user_list, index=user_list.index(cur_data['user']) if is_edit and cur_data['user'] in user_list else 0)
        date = st.date_input("日付", datetime.strptime(cur_data['date'], '%Y/%m/%d') if is_edit else datetime.now())
        event = st.text_input("行事名・件名", value=cur_data['event'] if is_edit else "")
        
        col_L, col_R = st.columns(2)
        with col_L:
            time = st.text_input("開始時間", value=cur_data['time'] if is_edit else "")
            location = st.text_input("場所", value=cur_data['location'] if is_edit else "")
        with col_R:
            dress = st.text_input("服装・持参物", value=cur_data['dress'] if is_edit else "")
            person = st.text_input("同行者", value=cur_data['person'] if is_edit else "")
        
        participants = st.text_input("参加人数など", value=cur_data['participants'] if is_edit else "")
        caution = st.text_area("内容・注意事項・申し送り", height=200, value=cur_data['caution'] if is_edit else "")

        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 上書き保存" if is_edit else "💾 新規保存", use_container_width=True):
                if event:
                    conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
                    sql_vals = (doc_type, user, date.strftime('%Y/%m/%d'), time, event, location, dress, person, participants, caution)
                    if is_edit:
                        cur.execute("UPDATE notes SET doc_type=?, user=?, date=?, time=?, event=?, location=?, dress=?, person=?, participants=?, caution=? WHERE id=?", sql_vals + (st.session_state.edit_id,))
                        st.success("更新完了！")
                    else:
                        cur.execute("INSERT INTO notes (doc_type, user, date, time, event, location, dress, person, participants, caution) VALUES (?,?,?,?,?,?,?,?,?,?)", sql_vals)
                        st.success("新規保存完了！")
                    conn.commit(); conn.close()
                else: st.error("行事名を入れてくれ。")
        with c2:
            if st.button("📄 PDF準備", use_container_width=True):
                data = {"doc_type": doc_type, "user": user, "date": date.strftime('%Y/%m/%d'), "time": time, "event": event, "location": location, "dress": dress, "person": person, "participants": participants, "caution": caution}
                pdf_path = generate_pdf(data)
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 PDF保存", f, file_name=f"PTA_{event}.pdf", use_container_width=True)
