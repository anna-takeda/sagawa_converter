import streamlit as st
import pandas as pd
import mojimoji
from datetime import datetime

def to_fullwidth(s: str) -> str:
    """半角→全角"""
    if not isinstance(s, str):
        return s
    return mojimoji.han_to_zen(s, ascii=True, digit=True, kana=True)

def main():
    st.title("佐川伝票変換システム")

    uploaded_file = st.file_uploader("CSVをアップロード", type=["csv"])
    if not uploaded_file:
        st.stop()

    df_raw = pd.read_csv(uploaded_file, encoding="cp932", header=None, dtype=str)
    if df_raw.shape[0] < 2:
        st.warning("2行目以降のデータがありません。")
        st.stop()

    header_row = df_raw.iloc[0].copy()
    data_df = df_raw.iloc[1:].copy().reset_index(drop=True)

    # 列インデックスを定義
    Y_COL_IDX = 24  # Y列(25列目)
    Z_COL_IDX = 25  # Z列(26列目)
    AZ_COL_IDX = 51 # AZ列(52列目)
    NAME_COL_IDX = 7 # お届け先名称1がある列(今回は列7と想定)

    st.write("### ▼アップロード内容（先頭3行）")
    st.dataframe(data_df.head(3))

    # フォーム内で Y列が空欄のものを入力
    data_df[Y_COL_IDX] = data_df[Y_COL_IDX].fillna("")
    missing_mask = data_df[Y_COL_IDX].str.strip() == ""
    missing_indices = data_df[missing_mask].index

    with st.form("fill_y_form"):
        if len(missing_indices) > 0:
            st.warning(f"商品名が空欄の行が {len(missing_indices)} 件あります。値を入力してください。")
            for idx in missing_indices:
                name_val = data_df.iat[idx, NAME_COL_IDX] or ""
                current_y = data_df.iat[idx, Y_COL_IDX] or ""
                st.text_input(
                    label=f"行 {idx} / 注文者：{name_val} の Y列",
                    key=f"y_input_{idx}",
                    value=current_y
                )
        else:
            st.info("商品名空欄はありません。")

        # フォーム送信ボタン：押したらY列更新 → 変換 → セッションへ保存
        submitted = st.form_submit_button("変換を実行")
        if submitted:
            # 1) Y列更新
            for idx in missing_indices:
                new_val = st.session_state.get(f"y_input_{idx}", "").strip()
                data_df.iat[idx, Y_COL_IDX] = new_val

            # 2) 変換処理
            for i in range(len(data_df)):
                val_y = data_df.iat[i, Y_COL_IDX] or ""
                full_val = to_fullwidth(val_y)
                if len(full_val) >= 17:
                    data_df.iat[i, Y_COL_IDX] = full_val[:16]
                    data_df.iat[i, Z_COL_IDX] = full_val[16:]
                else:
                    data_df.iat[i, Y_COL_IDX] = full_val

            # Y列ソート
            # data_df.sort_values(by=Y_COL_IDX, inplace=True)
            # data_df.reset_index(drop=True, inplace=True)

            # AZ列に"011"をセット
            # 列が足りない場合は追加
            if AZ_COL_IDX >= data_df.shape[1]:
                for _ in range(AZ_COL_IDX - data_df.shape[1] + 1):
                    data_df[data_df.shape[1]] = ""
            data_df[AZ_COL_IDX] = "011"

            # ヘッダー結合
            final_df = pd.concat([header_row.to_frame().T, data_df], ignore_index=True)

            st.session_state["final_df"] = final_df
            st.success("商品名の更新＆変換が完了しました！")

    # フォーム外でダウンロードボタンを表示
    if "final_df" in st.session_state:
        final_df = st.session_state["final_df"]
        st.write("### ▼変換後データ（先頭3行）")
        st.dataframe(final_df.head(3))
        
        # ▼ここが変更点：実行時日付をファイル名に入れる
        today_str = datetime.now().strftime('%Y%m%d')  # YYYYMMDD 形式
        file_name = f"{today_str}_sagawa_converted.csv"

        csv_str = final_df.to_csv(index=False, header=False, encoding="cp932")
        st.download_button(
            label="変換後CSVをダウンロード",
            data=csv_str.encode("cp932"),
            file_name=file_name,  # 日付入りファイル名
            mime="text/csv"
        )

if __name__ == "__main__":
    main()
