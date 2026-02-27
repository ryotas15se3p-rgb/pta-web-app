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

# --- ページ設定（スマホ最適化） ---
st.set_page_config(page_title="PTAクラウド支部", layout="centered")

# --- カスタムCSS（目に優しい配色を継承） ---
st.markdown("""
    <style>
    .stApp { background-color: #F0F4F8; }
    .main .block-container { padding-top: 2rem; }
    h1 { color: #2C3E50; font-size: 1.8rem; text-align: center; }
    .stButton>button { border-radius: 8px; height: 3em; transition: 0.3s; }
    /* 保存ボタン（緑） */
    div.stButton > button:first-child { background-color: #B8E0B8; color: #2C3E50; border: none; }
    /* PDF発行ボタン（青） */
    .pdf-btn > div > button { background-color: #AED9E0 !important; color: #2C3E50 !important; }
    </style>
    """, unsafe_allow_html=True)

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

# --- PDF生成エンジン（Webダウンロード用） ---
def generate_pdf(data):
    filepath = "pta_output.pdf"
    c = canvas.Canvas(filepath, pagesize=A4)
    # サーバー環境（Linux）でも動くよう、フォント設定は後ほど調整が必要な場合あり
    try:
        pdfmetrics.registerFont(TTFont('MS-Gothic', "C:/Windows/Fonts/msgothic.ttc"))
    except:
        # サーバー上（Linux等）でフォントが見つからない場合の回避策
        pass 
        
    c.setFont('MS-Gothic', 18)
    c.drawCentredString(105*mm, 280*mm, f"PTA{data['doc_type']}")
    c.line(25*mm, 275*mm, 185*mm, 275*mm)
    c.setFont('MS-Gothic', 11)
    y = 265
    items = [("入力者", data['user']), ("開催日", data['date']), ("時間", data['time']), 
             ("行事内容", data['event']), ("開催場所", data['location']), ("服装・持参物", data['dress']), 
             ("同行者", data['person']), ("参加者", data['participants'])]
    for l, v in items:
        if v:
            c.drawString(25*mm, y*mm, f"【{l}】: {v}")
            y -= 10
    c.drawString(25*mm, y*mm, "【内容・注意事項・申し送り】:")
    y -= 8
    t = c.beginText(30*mm, y*mm); t.setFont('MS-Gothic', 10); t.setLeading(15)
    for line in data['caution'].splitlines():
        for i in range(0, len(line), 45): t.textLine(line[i:i+45])
    c.drawText(t); c.showPage(); c.save()
    return filepath

# --- メイン画面構成 ---
init_db()
st.title("📱 PTA業務ハッピー化ツール")

tab1, tab2 = st.tabs(["📋 新規作成", "履歴確認"])

with tab1:
    # 入力フォーム
    doc_type = st.selectbox("書類種別", ["議事録", "備忘録"])
    user = st.selectbox("担当者", ["小此木", "澤田", "寺山"])
    date = st.date_input("開催日", datetime.now())
    time = st.text_input("開始時間", placeholder="例: AM 10:00")
    event = st.text_input("行事名・件名")
    
    col1, col2 = st.columns(2)
    with col1:
        location = st.text_input("場所")
        dress = st.text_input("服装")
    with col2:
        person = st.text_input("同行者")
        participants = st.text_input("参加者数など")
        
    caution = st.text_area("【注意事項・申し送り】", height=200)

    st.divider()

    # 保存ロジック（PC版のこだわりを継承）
    if st.button("💾 データのみ保存（下書き）"):
        if event:
            conn = sqlite3.connect("PTA_database.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO notes (doc_type, user, date, time, event, location, dress, person, participants, caution) VALUES (?,?,?,?,?,?,?,?,?,?)", 
                           (doc_type, user, date.strftime('%Y/%m/%d'), time, event, location, dress, person, participants, caution))
            conn.commit(); conn.close()
            st.success("データベースに保存したぜ！")
        else:
            st.error("行事名（件名）は必須だぜ！")

    # PDF発行セクション
    st.markdown('<div class="pdf-btn">', unsafe_allow_html=True)
    if st.button("📄 PDFファイルを準備する"):
        data = {"doc_type": doc_type, "user": user, "date": date.strftime('%Y/%m/%d'), "time": time, "event": event, 
                "location": location, "dress": dress, "person": person, "participants": participants, "caution": caution}
        pdf_path = generate_pdf(data)
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 PDFをダウンロード（スマホに保存）",
                data=f,
                file_name=f"PTA_{event}_{date.strftime('%m%d')}.pdf",
                mime="application/pdf"
            )
    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.subheader("過去の記録一覧")
    conn = sqlite3.connect("PTA_database.db")
    df = pd.read_sql_query("SELECT id, doc_type, date, event, user FROM notes ORDER BY date DESC", conn)
    conn.close()
    
    if not df.empty:
        # スマホで見やすいようにテーブル表示
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 簡易的な検索機能
        search_q = st.text_input("行事名で検索")
        if search_q:
            st.write(df[df['event'].str.contains(search_q)])
    else:
        st.info("まだ記録がないぜ。最初の1件を登録しよう！")