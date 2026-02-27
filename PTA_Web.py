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

# --- ページ設定 ---
st.set_page_config(page_title="PTAクラウド支部", layout="centered")

# --- ログイン認証 ---
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
            else:
                st.error("IDまたはパスワードが正しくありません。")
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

# --- PDF生成エンジン（複数ページ・日本語対応） ---
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
        canvas_obj.setFont(f_main, 11)

    page_count = 1
    draw_header(c, page_count)
    
    y = 265
    items = [
        ("担当者", data['user']), ("日付", data['date']), ("時間", data['time']), 
        ("行事名", data['event']), ("場所", data['location']), 
        ("服装・持参物", data['dress']), ("同行者", data['person']), ("参加人数", data['participants'])
    ]
    
    for label, val in items:
        if val:
            c.drawString(25*mm, y*mm, f"【{label}】: {val}")
            y -= 10
            
    c.drawString(25*mm, y*mm, "【内容・注意事項・申し送り】:")
    y -= 8
    
    # 本文の書き込み（自動改ページ処理）
    c.setFont(f_main, 10)
    lines = []
    caution_text = data['caution'] if data['caution'] else ""
    for raw_line in caution_text.splitlines():
        for i in range(0, len(raw_line), 35):
            lines.append(raw_line[i:i+35])
            
    for line in lines:
        if y < 20: 
            c.showPage()
            page_count += 1
            draw_header(c, page_count)
            y = 265
            c.setFont(f_main, 10)
            
        c.drawString(30*mm, y*mm, line)
        y -= 6
    
    c.showPage()
    c.save()
    return filepath

# --- メイン処理 ---
if check_password():
    init_db()
    if "current_user_id" in st.session_state:
        st.sidebar.write(f"ログイン中: {st.session_state['current_user_id']}")
    if st.sidebar.button("ログアウト"):
        st.session_state.clear(); st.rerun()

    st.title("📱 PTAクラウド支部 Ver.3.7")
    tab1, tab2 = st.tabs(["📝 新規入力・編集", "📚 履歴・データ管理"])

    if 'edit_id' not in st.session_state: st.session_state.edit_id = None

    with tab2:
        st.subheader("保存済みデータ一覧")
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM notes ORDER BY id DESC", conn)
        conn.close()
        
        if not df.empty:
            event_options = {f"ID:{r['id']} - {r['event']}": r['id'] for _, r in df.iterrows()}
            selected_key = st.selectbox("操作するデータを選択してください", list(event_options.keys()), index=None)
            
            if selected_key:
                target_id = event_options[selected_key]
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🔧 データを編集する", use_container_width=True):
                        st.session_state.edit_id = target_id; st.success("編集モードに切り替えました。")
                with c2:
                    if st.button("🗑️ データを削除する", type="primary", use_container_width=True):
                        conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
                        cur.execute(f"DELETE FROM notes WHERE id={target_id}")
                        conn.commit(); conn.close(); st.rerun()
            st.divider()
            st.dataframe(df[['id', 'date', 'event', 'user']], use_container_width=True, hide_index=True)
            
            # 会長専用バックアップ
            if st.session_state.get('current_user_id') == ADMIN_ID:
                with st.expander("🛠 管理者メニュー（バックアップ）"):
                    if os.path.exists(DB_FILE):
                        with open(DB_FILE, "rb") as f:
                            st.download_button("📥 データベースファイルをダウンロード", f, file_name=f"PTA_Backup.db", mime="application/octet-stream", use_container_width=True)
        else: st.write("保存されたデータはありません。")

    with tab1:
        is_edit = st.session_state.edit_id is not None
        if is_edit:
            st.info(f"💡 ID:{st.session_state.edit_id} のデータを編集中です。")
            conn = sqlite3.connect(DB_FILE)
            cur_data_df = pd.read_sql_query(f"SELECT * FROM notes WHERE id={st.session_state.edit_id}", conn)
            conn.close()
            if not cur_data_df.empty: cur_data = cur_data_df.iloc[0]
            else: st.session_state.edit_id = None; st.rerun()
            if st.button("❌ 編集をキャンセル"): st.session_state.edit_id = None; st.rerun()
        
        doc_type = st.selectbox("書類種別", ["議事録", "備忘録"], index=0 if not is_edit else (0 if cur_data['doc_type']=="議事録" else 1))
        user_list = ["小此木", "澤田", "寺山"]
        user_idx = user_list.index(cur_data['user']) if is_edit and cur_data['user'] in user_list else 0
        user = st.selectbox("担当者", user_list, index=user_idx)
        date = st.date_input("日付", datetime.strptime(cur_data['date'], '%Y/%m/%d') if is_edit else datetime.now())
        event = st.text_input("行事名・件名", value=cur_data['event'] if is_edit else "")
        
        c_l, c_r = st.columns(2)
        with c_l:
            time = st.text_input("時間", value=cur_data['time'] if is_edit else "")
            location = st.text_input("場所", value=cur_data['location'] if is_edit else "")
        with c_r:
            dress = st.text_input("服装・持参物", value=cur_data['dress'] if is_edit else "")
            person = st.text_input("同行者", value=cur_data['person'] if is_edit else "")
        
        participants = st.text_input("参加人数など", value=cur_data['participants'] if is_edit else "")
        caution = st.text_area("内容・注意事項・申し送り", height=200, value=cur_data['caution'] if is_edit else "")

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            label = "🆙 上書き保存" if is_edit else "💾 新規保存"
            if st.button(label, use_container_width=True):
                if event:
                    conn = sqlite3.connect(DB_FILE); cur = conn.cursor()
                    v = (doc_type, user, date.strftime('%Y/%m/%d'), time, event, location, dress, person, participants, caution)
                    if is_edit: cur.execute("UPDATE notes SET doc_type=?, user=?, date=?, time=?, event=?, location=?, dress=?, person=?, participants=?, caution=? WHERE id=?", v + (st.session_state.edit_id,))
                    else: cur.execute("INSERT INTO notes (doc_type, user, date, time, event, location, dress, person, participants, caution) VALUES (?,?,?,?,?,?,?,?,?,?)", v)
                    conn.commit(); conn.close(); st.success("データを保存しました。")
                else: st.error("行事名を入力してください。")
        with c2:
            if st.button("📄 PDFを作成する", use_container_width=True):
                d = {"doc_type": doc_type, "user": user, "date": date.strftime('%Y/%m/%d'), "time": time, "event": event, "location": location, "dress": dress, "person": person, "participants": participants, "caution": caution}
                pdf_path = generate_pdf(d)
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 PDFをダウンロード", f, file_name=f"PTA_{event}.pdf", use_container_width=True)
