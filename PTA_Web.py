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

# --- PDF生成エンジン（フォント同梱・絶対エラー出さない仕様） ---
def generate_pdf(data):
    filepath = "pta_output.pdf"
    c = canvas.Canvas(filepath, pagesize=A4)
    
    # フォントの設定（GitHubに上げたmsgothic.ttcを読み込む）
    font_path = "msgothic.ttc"
    font_name = "MS-Gothic-Web" # 登録名が重複しないように別名で
    
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
            f_main = font_name
        except:
            f_main = "Helvetica" # 万が一のバックアップ
    else:
        f_main = "Helvetica"

    # タイトル
    c.setFont(f_main, 18)
    c.drawCentredString(105*mm, 280*mm, f"PTA {data['doc_type']}")
    c.line(25*mm, 275*mm, 185*mm, 275*mm)
    
    # 項目
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
    
    # 本文（長文対応）
    t = c.beginText(30*mm, y*mm)
    t.setFont(f_main, 10)
    t.setLeading(15)
    for line in data['caution'].splitlines():
        # 日本語の折り返し簡易処理（40文字程度）
        for i in range(0, len(line), 40):
            t.textLine(line[i:i+40])
    
    c.drawText(t)
    c.showPage()
    c.save()
    return filepath

# --- 画面構成 ---
init_db()
st.title("📱 PTA業務ハッピー化ツール")

tab1, tab2 = st.tabs(["📋 新規作成", "📚 履歴確認"])

with tab1:
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
        
    caution = st.text_area("【内容・注意事項・申し送り】", height=200)

    st.divider()

    # 1. 保存ボタン
    if st.button("💾 データベースに保存"):
        if event:
            conn = sqlite3.connect("PTA_database.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO notes (doc_type, user, date, time, event, location, dress, person, participants, caution) VALUES (?,?,?,?,?,?,?,?,?,?)", 
                           (doc_type, user, date.strftime('%Y/%m/%d'), time, event, location, dress, person, participants, caution))
            conn.commit()
            conn.close()
            st.success("保存完了！履歴タブから確認できるぜ。")
        else:
            st.warning("行事名を入力してくれよな。")

    # 2. PDF生成・ダウンロード
    if st.button("📄 PDFファイルを準備する"):
        data = {
            "doc_type": doc_type, "user": user, "date": date.strftime('%Y/%m/%d'), 
            "time": time, "event": event, "location": location, "dress": dress, 
            "person": person, "participants": participants, "caution": caution
        }
        pdf_path = generate_pdf(data)
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 PDFをダウンロード（スマホ保存）",
                data=f,
                file_name=f"PTA_{event}.pdf",
                mime="application/pdf"
            )

with tab2:
    st.subheader("過去の記録一覧")
    conn = sqlite3.connect("PTA_database.db")
    df = pd.read_sql_query("SELECT id, doc_type, date, event, user FROM notes ORDER BY id DESC", conn)
    conn.close()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.info("※詳細は今のところPC版で見てくれ。Web版も追々パワーアップさせるぜ！")
    else:
        st.write("まだデータがないぜ。")
