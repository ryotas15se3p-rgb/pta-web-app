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
# ここを変えれば会長専用の鍵になるぜ！
ADMIN_ID = "admin"        # 管理者（会長）ID
ADMIN_PASS = "pta700"     # 管理者パスワード

# 一般役員用などの追加も可能だけど、今はこれで行くぜ
DB_FILE = "PTA_database.db"

# --- ページ設定 ---
st.set_page_config(page_title="PTAクラウド支部", layout="centered")

# --- ログインチェック（IDを保持するように改良） ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 PTAクラウド支部 入室管理")
        u = st.text_input("ID")
        p = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if u == ADMIN_ID and p == ADMIN_PASS:
                st.session_state["password_correct"] = True
                st.session_state["current_user_id"] = u # ログインIDを記録
                st.rerun()
            else:
                st.error("IDかパスワードが違うぜ。")
        return False
    return True

# --- データベース初期化 ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doc_type TEXT, user TEXT, date TEXT, time TEXT, event TEXT,
        location TEXT, dress TEXT, person TEXT, participants TEXT, caution TEXT
    )''')
    conn.commit(); conn.close()

# --- PDF生成エンジン（フルスペック） ---
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
    
    c.setFont(f_main, 18)
    c.drawCentredString(105*mm, 280*mm, f"PTA {data['doc_type']}")
    c.line(20*mm, 275*mm, 190*mm, 275*mm)
    c.setFont(f_main, 11)
    y = 265
    items = [
        ("入力者", data['user']), ("開催日", data['date']), ("時間", data['time']), 
        ("行事内容", data['event']), ("開催場所", data['location']), 
        ("服装・持参物", data['dress']), ("同行者", data['person']), ("参加者", data['participants'])
    ]
    for label, val in items:
        if val:
            c.drawString(25*mm, y*mm, f"【{label}】: {val}")
            y -= 10
    c.drawString(25*mm, y*mm, "【内容・注意事項・申し送り】:")
    t = c.beginText(30*mm, (y-8)*mm); t.setFont(f_main, 10); t.setLeading(15)
    caution_text = data['caution'] if data['caution'] else ""
    for line in caution_text.splitlines():
        for i in range(0, len(line), 35): t.textLine(line[i:i+35])
    c.drawText(t); c.showPage(); c.save()
    return filepath

# --- メイン処理 ---
if check_password():
    init_db()
    st.sidebar.write(f"Login ID: {st.session_state['current_user_id']}")
    if st.sidebar.button("ログアウト"):
        st.session_state.clear()
        st.rerun()

    st.title("📱 PTAクラウド支部 Ver.3.3")
    tab1, tab2 = st.tabs(["📝 入力・編集", "📚 履歴・管理"])

    with tab2:
        st.subheader("保存済みデータ一覧")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM notes ORDER BY id DESC", conn)
        conn.close()
        
        if not df.empty:
            event_options = {f"ID:{r['id']} - {r['event']}": r['id'] for _, r in df.iterrows()}
            selected_key = st.selectbox("データを選択", list(event_options.keys()), index=None)
            
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
            
            # --- 🔐 ここが管理者限定の「隠し金庫」 ---
            if st.session_state['current_user_id'] == ADMIN_ID:
                with st.expander("🛠 管理者専用ツール（バックアップ）"):
                    st.write("このボタンは会長（admin）にしか見えてないぜ。")
                    if os.path.exists(DB_FILE):
                        with open(DB_FILE, "rb") as f:
                            st.download_button(
                                "📥 DBファイルをスマホに保存", 
                                f, 
                                file_name=f"PTA_Backup_{datetime.now().strftime('%Y%m%d')}.db", 
                                mime="application/octet-stream", 
                                use_container_width=True
                            )
        else: st.write("データなし。")

    with tab1:
        if 'edit_id' not in st.session_state: st.session_state.edit_id = None
        is_edit = st.session_state.edit_id is not None
        
        if is_edit:
            st.info(f"💡 ID:{st.session_state.edit_id} を編集中")
            conn = sqlite3.connect(DB_FILE)
            cur_data = pd.read_sql_query(f"SELECT * FROM notes WHERE id={st.session_state.edit_id}", conn).iloc[0]
            conn.close()
            if st.button("❌ 編集キャンセル"):
                st.session_state.edit_id = None; st.rerun()

        # フルスペック入力フォーム
        doc_type = st.selectbox("書類", ["議事録", "備忘録"], index=0 if not is_edit else (0 if cur_data['doc_type']=="議事録" else 1))
        user_list = ["小此木", "澤田", "寺山"]
        user = st.selectbox("担当", user_list, index=user_list.index(cur_data['user']) if is_edit and cur_data['user'] in user_list else 0)
        date = st.date_input("日付", datetime.strptime(cur_data['date'], '%Y/%m/%d') if is_edit else datetime.now())
        event = st.text_input("行事名・件名", value=cur_data['event'] if is_edit else "")
        
        c_l, c_r = st.columns(2)
        with c_l:
            time = st.text_input("時間", value=cur_data['time'] if is_edit else "")
            location = st.text_input("場所", value=cur_data['location'] if is_edit else "")
        with c_r:
            dress = st.text_input("服装", value=cur_data['dress'] if is_edit else "")
            person = st.text_input("同行者", value=cur_data['person'] if is_edit else "")
        
        participants = st.text_input("参加人数", value=cur_data['participants'] if is_edit else "")
        caution = st.text_area("内容・申し送り", height=200, value=cur_data['caution'] if is_edit else "")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 上書き保存" if is_edit else "💾 新規保存", use_container_width=True):
                if event:
                    conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
                    vals = (doc_type, user, date.strftime('%Y/%m/%d'), time, event, location, dress, person, participants, caution)
                    if is_edit:
                        cur.execute("UPDATE notes SET doc_type=?, user=?, date=?, time=?, event=?, location=?, dress=?, person=?, participants=?, caution=? WHERE id=?", vals + (st.session_state.edit_id,))
                        st.success("更新完了！")
                    else:
                        cur.execute("INSERT INTO notes (doc_type, user, date, time, event, location, dress, person, participants, caution) VALUES (?,?,?,?,?,?,?,?,?,?)", vals)
                        st.success("保存完了！")
                    conn.commit(); conn.close()
                else: st.error("行事名を入れてくれ。")
        with c2:
            if st.button("📄 PDF準備", use_container_width=True):
                data = {"doc_type": doc_type, "user": user, "date": date.strftime('%Y/%m/%d'), "time": time, "event": event, "location": location, "dress": dress, "person": person, "participants": participants, "caution": caution}
                pdf_path = generate_pdf(data)
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 PDF保存", f, file_name=f"PTA_{event}.pdf", use_container_width=True)
