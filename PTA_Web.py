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

# --- PDF生成エンジン（日本語対応版） ---
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
st.title("📱 PTAクラウド支部 Ver.2.1")

# 状態管理（編集対象のIDを保持）
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

tab1, tab2 = st.tabs(["📝 入力・編集", "📚 履歴・管理"])

with tab2:
    st.subheader("保存済みデータ一覧")
    conn = sqlite3.connect("PTA_database.db")
    df = pd.read_sql_query("SELECT * FROM notes ORDER BY id DESC", conn)
    conn.close()
    
    if not df.empty:
        # 編集・削除対象の選択
        # セレクトボックスにIDと行事名を表示して選びやすくする
        event_options = {f"ID:{row['id']} - {row['event']}": row['id'] for _, row in df.iterrows()}
        selected_key = st.selectbox("操作したいデータを選択", list(event_options.keys()), index=None, placeholder="データを選択...")
        
        if selected_key:
            target_id = event_options[selected_key]
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🔧 編集モードで読み込む", use_container_width=True):
                    st.session_state.edit_id = target_id
                    st.success(f"ID:{target_id} を読み込んだぜ！『入力・編集』タブへGO！")
            
            with col_b:
                # 削除は間違い防止のために「本当に消す？」チェックを入れる
                if st.button("🗑️ このデータを完全削除", type="primary", use_container_width=True):
                    conn = sqlite3.connect("PTA_database.db")
                    cursor = conn.cursor()
                    cursor.execute(f"DELETE FROM notes WHERE id={target_id}")
                    conn.commit()
                    conn.close()
                    st.session_state.edit_id = None # 編集中のやつだったら解除
                    st.warning(f"ID:{target_id} を抹消したぜ。")
                    st.rerun()
        
        st.divider()
        st.dataframe(df[['id', 'date', 'event', 'user']], use_container_width=True, hide_index=True)
    else:
        st.write("まだデータがないぜ。")

with tab1:
    is_edit = st.session_state.edit_id is not None
    
    if is_edit:
        st.info(f"💡 現在、ID:{st.session_state.edit_id} を編集中だぜ。")
        conn = sqlite3.connect("PTA_database.db")
        cur_data = pd.read_sql_query(f"SELECT * FROM notes WHERE id={st.session_state.edit_id}", conn).iloc[0]
        conn.close()
        if st.button("❌ 編集をキャンセルして新規作成に戻る"):
            st.session_state.edit_id = None
            st.rerun()
    else:
        st.info("🆕 新規作成モードだ。")

    # --- 入力フォーム ---
    doc_type = st.selectbox("書類種別", ["議事録", "備忘録"], index=0 if not is_edit else (0 if cur_data['doc_type']=="議事録" else 1))
    
    user_list = ["小此木", "澤田", "寺山"]
    # 既存のユーザーがリストにあるかチェックして初期値を設定
    default_user_idx = 0
    if is_edit and cur_data['user'] in user_list:
        default_user_idx = user_list.index(cur_data['user'])
    user = st.selectbox("担当者", user_list, index=default_user_idx)
    
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

    # --- アクションボタン ---
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆙 上書き保存" if is_edit else "💾 新規保存", use_container_width=True):
            if event:
                conn = sqlite3.connect("PTA_database.db")
                cursor = conn.cursor()
                if is_edit:
                    cursor.execute("""UPDATE notes SET doc_type=?, user=?, date=?, time=?, event=?, location=?, dress=?, person=?, participants=?, caution=? WHERE id=?""",
                                   (doc_type, user, date.strftime('%Y/%m/%d'), time, event, location, dress, person, participants, caution, st.session_state.edit_id))
                    st.success("アップデート完了だ！")
                else:
                    cursor.execute("INSERT INTO notes (doc_type, user, date, time, event, location, dress, person, participants, caution) VALUES (?,?,?,?,?,?,?,?,?,?)", 
                                   (doc_type, user, date.strftime('%Y/%m/%d'), time, event, location, dress, person, participants, caution))
                    st.success("新規登録したぜ！")
                conn.commit(); conn.close()
            else:
                st.error("行事名がないと保存できないぜ。")

    with col2:
        if st.button("📄 PDF準備", use_container_width=True):
            data = {"doc_type": doc_type, "user": user, "date": date.strftime('%Y/%m/%d'), "time": time, "event": event, "location": location, "dress": dress, "person": person, "participants": participants, "caution": caution}
            pdf_path = generate_pdf(data)
            with open(pdf_path, "rb") as f:
                st.download_button("📥 PDF保存", f, file_name=f"PTA_{event}.pdf", use_container_width=True)
