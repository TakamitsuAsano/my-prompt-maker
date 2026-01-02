import streamlit as st
import pandas as pd
import glob
import os
import re

# ---------------------------------------------------------
# 設定と関数
# ---------------------------------------------------------

st.set_page_config(
    page_title="ビジネス0=>1アクション生成アプリ",
    page_icon="🚀",
    layout="wide"
)

# CSSによるスタイル調整（見やすさ向上）
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .stTextArea textarea {
        background-color: #ffffff;
        color: #31333F;
    }
    .instruction-box {
        background-color: #e8f0fe;
        border-left: 5px solid #4285f4;
        padding: 15px;
        margin-bottom: 20px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data(data_dir="data"):
    """
    dataフォルダ内の全CSVファイルを読み込み、結合してDataFrameを返す関数
    ファイル名から「大項目」カテゴリを抽出します。
    """
    all_files = glob.glob(os.path.join(data_dir, "*.csv"))
    
    if not all_files:
        return None

    df_list = []
    
    for filename in all_files:
        try:
            # CSV読み込み（エンコーディングはShift-JISやUTF-8など環境に合わせて自動調整が必要な場合があります）
            # 今回提供されたファイルはShift-JISやCP932の可能性が高いですが、pd.read_csvはデフォルトUTF-8
            # エラーが出た場合は encoding='cp932' などを試行するロジックを入れています
            try:
                df = pd.read_csv(filename, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(filename, encoding='cp932')

            # ファイル名から大項目名を抽出（例: "経営AI研修プロンプト集 - 新商品アイデア.csv" -> "新商品アイデア"）
            basename = os.path.basename(filename)
            category_name = basename.replace("経営AI研修プロンプト集 - ", "").replace(".csv", "").replace(" のコピー", "")
            
            # カラム整理（スニペットに基づき調整）
            # 想定カラム: カテゴリ, 番号, (空), 想定シーン, プロンプト本文
            # 必要なカラムのみ抽出し、名前を統一
            if len(df.columns) >= 5:
                # 3列目が空列の場合が多いので、名前で指定するか位置で指定
                # ここではカラム名に含まれるキーワードで判定
                col_scene = [c for c in df.columns if "想定シーン" in c][0]
                col_prompt = [c for c in df.columns if "プロンプト" in c][0]
                col_sub_cat = [c for c in df.columns if "カテゴリ" in c][0]
                
                df_filtered = df[[col_sub_cat, col_scene, col_prompt]].copy()
                df_filtered.columns = ["小カテゴリ", "想定シーン", "プロンプト本文"]
                df_filtered["大項目"] = category_name
                
                # 空行削除
                df_filtered = df_filtered.dropna(subset=["プロンプト本文"])
                df_list.append(df_filtered)
        except Exception as e:
            st.error(f"ファイル {filename} の読み込みに失敗しました: {e}")

    if df_list:
        return pd.concat(df_list, ignore_index=True)
    else:
        return None

def extract_placeholders(text):
    """
    プロンプトテキストから 【 】 や [ ] で囲まれた箇所を抽出する
    """
    # 【 】または [ ] で囲まれた文字列を抽出（改行を含まない短いもの）
    patterns = r'[【\[](.+?)[】\]]'
    matches = re.findall(patterns, text)
    # 重複排除してリスト化
    return list(set(matches))

# ---------------------------------------------------------
# メイン画面
# ---------------------------------------------------------

st.title("🚀 ビジネス0=>1アクション生成アプリ")
st.markdown("困った時の壁打ち相手。状況を入力して、生成されたプロンプトを **NotebookLM** に貼り付けてください。")

# データ読み込み
df = load_data()

if df is None:
    st.warning("⚠️ 'data' フォルダにCSVファイルが見つかりません。Githubリポジトリの構成を確認してください。")
    st.stop()

# --- サイドバー：検索とフィルタ ---
st.sidebar.header("🔍 検索・絞り込み")

# 1. キーワード検索
search_query = st.sidebar.text_input("キーワード検索", placeholder="例：議事録、壁打ち、クレーム...")

# 2. 大項目の選択
all_categories = df["大項目"].unique()
selected_category = st.sidebar.selectbox("分野（大項目）を選択", ["すべて"] + list(all_categories))

# フィルタリング処理
filtered_df = df.copy()
if selected_category != "すべて":
    filtered_df = filtered_df[filtered_df["大項目"] == selected_category]

if search_query:
    filtered_df = filtered_df[
        filtered_df["想定シーン"].str.contains(search_query, case=False, na=False) | 
        filtered_df["小カテゴリ"].str.contains(search_query, case=False, na=False)
    ]

# --- メインコンテンツ ---

if filtered_df.empty:
    st.info("条件に一致するプロンプトが見つかりませんでした。")
else:
    # シーン選択（ラジオボタンだと数が多いのでセレクトボックス推奨）
    # 表示用に "【大項目】シーン" の形にする
    filtered_df["display_label"] = "【" + filtered_df["大項目"] + "】 " + filtered_df["想定シーン"].str[:40] + "..."
    
    selected_scene_label = st.selectbox(
        "⚡ 想定シーンを選んでください",
        filtered_df["display_label"].tolist()
    )
    
    # 選択された行を取得
    selected_row = filtered_df[filtered_df["display_label"] == selected_scene_label].iloc[0]
    raw_prompt = selected_row["プロンプト本文"]
    
    st.markdown("---")
    
    # --- 2カラムレイアウト ---
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("📝 ステップ1: 情報入力")
        st.caption("プロンプト内の【 】の部分を入力してください。空欄のままにすると元の【 】が残ります。")
        
        # プレースホルダーの自動検出と入力フォーム生成
        placeholders = extract_placeholders(raw_prompt)
        user_inputs = {}
        
        if placeholders:
            for ph in placeholders:
                # 入力不要そうな見出し等は除外するロジックを入れても良いが、
                # ここではユーザーに判断させるため全て表示する
                val = st.text_input(f"【{ph}】 の内容", key=ph)
                if val:
                    user_inputs[ph] = val
        else:
            st.info("入力が必要な項目は自動検出されませんでした。そのままプロンプトを利用できます。")

    with col2:
        st.subheader("🤖 ステップ2: NotebookLMへ")
        
        # NotebookLM推奨ソースの表示ロジック
        st.markdown('<div class="instruction-box">', unsafe_allow_html=True)
        st.markdown("**💡 NotebookLM アップロード推奨資料**")
        
        cat = selected_row["大項目"]
        if "商品" in cat or "アイデア" in cat:
            st.markdown("- 企画メモ、会議の議事録、ブレストのホワイトボード写真")
        elif "競合" in cat or "分析" in cat:
            st.markdown("- 調査データのExcel/PDF、業界レポート、過去の売上データ")
        elif "マーケティング" in cat or "広報" in cat:
            st.markdown("- 既存の商品パンフレット、過去のプレスリリース、顧客アンケート結果")
        elif "ナレッジ" in cat or "組織" in cat:
            st.markdown("- 社内規定、組織図、業務マニュアル、日報")
        else:
            st.markdown("- 関連する会議の議事録、または現状のメモ書き（PDF/Text）")
            
        st.markdown("<small>※資料がない場合でも、Geminiが一般的なコンサルタントとして回答します。</small>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # プロンプトの置換処理
        final_prompt = raw_prompt
        for ph, val in user_inputs.items():
            # 【 】 と [ ] の両方のパターンに対応して置換
            final_prompt = final_prompt.replace(f"【{ph}】", val).replace(f"[{ph}]", val)

        # データソース考慮の指示を追加（オプション）
        add_instruction = st.checkbox("データソース（議事録など）の内容を踏まえる指示を追加する", value=True)
        if add_instruction:
            header_instruction = "【重要】添付したソース（議事録や資料）の内容を前提知識として踏まえた上で、以下の指示に従ってください。\n\n"
            final_prompt = header_instruction + final_prompt

        st.text_area("完成プロンプト (右上のアイコンからコピーできます)", value=final_prompt, height=400)
        
        st.success("👆 上記をコピーして、NotebookLMのチャット欄に貼り付けてください！")