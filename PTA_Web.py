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

# --- PDF生成エンジン（■対策：フォント絶対パス指定版） ---
def generate_pdf(data):
    filepath = "PTA_Output.pdf"
    c = canvas.Canvas(filepath, pagesize=A4)
    
    # サーバー上のカレントディレクトリを確実に取得
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # GitHubに上げたフォントファイル名。大文字小文字が違うならここを直してな！
    font_file = "msgothic.ttc" 
    font_path = os.path.join(base_dir, font_file)
    
    # フォント登録の儀式
    font_name = "MS-Gothic-Web"
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            f_main = font_name
        except Exception as e:
            st.error(f"フォント登録でエラーだぜ: {e}")
            f_main = "Helvetica"
    else:
        st.error(f"フォントファイル『{font_file}』が倉庫に見当たらないぜ！")
        f_main = "Helvetica"

    # --- 描画開始 ---
    c.setFont(f_main, 18)
    c.drawCentredString(105*mm, 280*mm, f"PTA {data['doc_type']}")
    c.line(20*mm, 275*mm, 190*mm, 275*mm)
    
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
    
    # 本文（長文の折り返し）
    t = c.beginText(30*mm, y*mm)
    t.setFont(f_main, 10)
    t.setLeading(15)
    
    caution_text = data['caution'] if data['caution'] else ""
    for line in caution_text.splitlines():
        # 全角35文字程度で改行
        for i in range(0, len(line), 35):
            t.textLine(line[i:i+35])
    
    c.drawText(t)
    c.showPage()
    c.save()
    return filepath

# --- 画面レイアウト ---
init_db()
st.title("📱 PTAクラウド支部")

tab1, tab2 = st.tabs(["📋 新規入力", "📚 履歴"])

with tab1:
    doc_type = st.selectbox("書類種別", ["議事録", "備忘録"])
    user = st.selectbox("担当者", ["小此木", "澤田", "寺山"])
    date = st.date_input("開催日", datetime.now())
    event = st.text_input("行事名・件名（必須）")
    
    with st.expander("詳細（場所・時間など）"):
        time = st.text_input("開始時間")
        location = st.text_input("場所")
        dress = st.text_input("服装・持参物")
        person = st.text_input("同行者")
        participants = st.text_input("参加人数など")
        
    caution = st.text_area("内容・注意事項・申し送り", height=200)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存（下書き）"):
            if event:
                conn = sqlite3.connect("PTA_database.db")
                cursor = conn.cursor()
                cursor.execute("INSERT INTO notes (doc_type, user, date, time, event, location, dress, person, participants, caution) VALUES (?,?,?,?,?,?,?,?,?,?)", 
                               (doc_type, user, date.strftime('%Y/%m/%d'), time, event, location, dress, person, participants, caution))
                conn.commit()
                conn.close()
                st.success("データベースに保存したぜ！")
            else:
                st.warning("行事名を入れてくれよな。")

    with col2:
        if st.button("📄 PDF準備"):
            data = {
                "doc_type": doc_type, "user": user, "date": date.strftime('%Y/%m/%d'), 
                "time": time, "event": event, "location": location, "dress": dress, 
                "person": person, "participants": participants, "caution": caution
            }
            pdf_path = generate_pdf(data)
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 PDFをダウンロード",
                    data=f,
                    file_name=f"PTA_{event}.pdf",
                    mime="application/pdf"
                )

with tab2:
    st.subheader("保存済みデータ")
    conn = sqlite3.connect("PTA_database.db")
    df = pd.read_sql_query("SELECT id, doc_type, date, event, user FROM notes ORDER BY id DESC", conn)
    conn.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.write("まだデータがないぜ。")
