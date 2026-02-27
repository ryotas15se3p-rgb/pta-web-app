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

# --- ページ設定 ---
st.set_page_config(page_title="PTAクラウド支部", layout="centered")

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
        except:
            f_main = "Helvetica"
    else:
        f_main = "Helvetica"
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
init_db()
st.title("📱 PTAクラウド支部 Ver.2.0")

# セッション状態（編集中のデータを保持）
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

tab1, tab2 = st.tabs(["📝 入力・編集", "📚 履歴"])

with tab2:
    st.subheader("過去の記録一覧")
    conn = sqlite3.connect("PTA_database.db")
    df = pd.read_sql_query("SELECT * FROM notes ORDER BY id DESC", conn)
    conn.close()
    
    if not df.empty:
        # 編集したい行を選択
        selected_event = st.selectbox("編集したい行事を選択してくれ", df['event'].tolist(), index=None, placeholder="行事を選んで編集開始...")
        
        if selected_event:
            row = df[df['event'] == selected_event].iloc[0]
            if st.button("🔧 このデータを編集モードで読み込む"):
                st.session_state.edit_id = int(row['id'])
                st.success(f"ID:{st.session_state.edit_id} を読み込んだぜ！『入力・編集』タブへ移動してくれ。")
        
        st.divider()
        st.dataframe(df[['id', 'date', 'event', 'user']], use_container_width=True, hide_index=True)
    else:
        st.write("まだデータがないぜ。")

with tab1:
    # 編集モードの判定
    is_edit = st.session_state.edit_id is not None
    if is_edit:
        st.info(f"💡 現在、ID:{st.session_state.edit_id} を編集してるぜ。")
        conn = sqlite3.connect("PTA_database.db")
        cur_data = pd.read_sql_query(f"SELECT * FROM notes WHERE id={st.session_state.edit_id}", conn).iloc[0]
        conn.close()
        if st.button("❌ 編集をキャンセルして新規作成に戻る"):
            st.session_state.edit_id = None
            st.rerun()
    else:
        st.info("🆕 新規作成モードだ。")

    # 入力フォーム（編集モードなら既存データを入れる）
    doc_type = st.selectbox("書類種別", ["議事録", "備忘録"], index=0 if not is_edit else (0 if cur_data['doc_type']=="議事録" else 1))
    user_list = ["小此木", "澤田", "寺山"]
    user_idx = user_list.index(cur_data['user']) if is_edit and cur_data['user'] in user_list else 0
    user = st.selectbox("担当者", user_list, index=user_idx)
    
    date_val = datetime.strptime(cur_data['date'], '%Y/%m/%d') if is_edit else datetime.now()
    date = st.date_input("開催日", date_val)
    event = st.text_input("行事名・件名", value=cur_data['event'] if is_edit else "")
    
    with st.expander("詳細（場所・時間など）"):
        time = st.text_input("開始時間", value=cur_data['time'] if is_edit else "")
        location = st.text_input("場所", value=cur_data['location'] if is_edit else "")
        dress = st.text_input("服装・持参物", value=cur_data['dress'] if is_edit else "")
        person = st.text_input("同行者", value=cur_data['person'] if is_edit else "")
        participants = st.text_input("参加人数", value=cur_data['participants'] if is_edit else "")
        
    caution = st.text_area("内容・注意事項", height=200, value=cur_data['caution'] if is_edit else "")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        btn_label = "🆙 上書き保存" if is_edit else "💾 新規保存"
        if st.button(btn_label):
            if event:
                conn = sqlite3.connect("PTA_database.db")
                cursor = conn.cursor()
                if is_edit:
                    cursor.execute("""UPDATE notes SET doc_type=?, user=?, date=?, time=?, event=?, location=?, dress=?, person=?, participants=?, caution=? WHERE id=?""",
                                   (doc_type, user, date.strftime('%Y/%m/%d'), time, event, location, dress, person, participants, caution, st.session_state.edit_id))
                    st.success("データを更新したぜ！")
                else:
                    cursor.execute("INSERT INTO notes (doc_type, user, date, time, event, location, dress, person, participants, caution) VALUES (?,?,?,?,?,?,?,?,?,?)", 
                                   (doc_type, user, date.strftime('%Y/%m/%d'), time, event, location, dress, person, participants, caution))
                    st.success("新しく保存したぜ！")
                conn.commit()
                conn.close()
            else:
                st.warning("行事名は必須だぜ！")

    with col2:
        if st.button("📄 PDF準備"):
            data = {"doc_type": doc_type, "user": user, "date": date.strftime('%Y/%m/%d'), "time": time, "event": event, "location": location, "dress": dress, "person": person, "participants": participants, "caution": caution}
            pdf_path = generate_pdf(data)
            with open(pdf_path, "rb") as f:
                st.download_button("📥 PDF保存", f, file_name=f"PTA_{event}.pdf")

    if is_edit:
        st.divider()
        if st.button("🗑️ このデータを完全に削除する", type="secondary"):
            conn = sqlite3.connect("PTA_database.db")
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM notes WHERE id={st.session_state.edit_id}")
            conn.commit(); conn.close()
            st.session_state.edit_id = None
            st.warning("削除したぜ。")
            st.rerun()
