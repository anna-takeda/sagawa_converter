import streamlit as st
import pandas as pd
import io
import mojimoji  # pip install mojimoji

st.set_page_config(
    page_title="CSV変換ツール",
    page_icon="📝",
    layout="centered"
)

def to_fullwidth(s: str) -> str:
    """
    半角を全角に変換する関数。
    （ascii=True, digit=True, kana=True）
    """
    if not isinstance(s, str):
        return s
    return mojimoji.han_to_zen(s, ascii=True, digit=True, kana=True)

def main():
    st.title("CSV変換ツール")
    st.write("""
    **▼主な機能**  
    1. **Y列(25列目)の空欄を手入力で補完**  
    2. **Y列を全角変換し、17文字目以降をZ列(26列目)へ移動**  
    3. **Y列で昇順ソート**  
    4. **AZ列(52列目)に「001」をセット**  
    5. **その他の列は変更しない**  
    """)

    uploaded_file = st.file_uploader(
        "CSVファイルをアップロードしてください（Shift-JIS想定）",
        type=["csv"],
    )

    if uploaded_file is not None:
        try:
            # 読み込み（ヘッダーなし）
            df_raw = pd.read_csv(uploaded_file, encoding="cp932", header=None, dtype=str)
            if df_raw.shape[0] < 2:
                st.warning("アップロードされたファイルには2行目以降がありません。2行以上のCSVをご用意ください。")
                return

            # 1行目をヘッダーとして保持、2行目以降をデータとする
            header_row = df_raw.iloc[0].copy()
            data_df = df_raw.iloc[1:].copy()

            st.write("### ▼アップロード内容（先頭3行）")
            st.dataframe(data_df.head(3))

            # --------------------------------------------------
            # 1) Y列が空欄のものをユーザーに入力してもらう
            # --------------------------------------------------
            # Y列(Excelで25列目) = 0ベース24
            Y_col_idx = 24

            # Y列が "NaN" または 空文字 の行を抽出
            # （str.strip() の前に、文字列以外(NaN含む)の場合に備えて fillna("") しておく）
            data_df[Y_col_idx] = data_df[Y_col_idx].fillna("")
            missing_y_mask = data_df[Y_col_idx].str.strip() == ""
            missing_indices = data_df[missing_y_mask].index

            # 空欄の行がある場合だけフォーム表示
            if len(missing_indices) > 0:
                st.warning(f"Y列が空欄のデータが {len(missing_indices)} 件あります。値を入力してください。")
                with st.form("fill_y_form"):
                    # 行ごとに text_input
                    for idx in missing_indices:
                        current_val = data_df.at[idx, Y_col_idx]
                        # key は重複しないように (row番号などを付与)
                        st.text_input(
                            label=f"行 {idx} の Y列(25列目)",
                            key=f"yvalue_{idx}",
                            value=current_val  # 初期値は空だが、一応取得
                        )
                    submitted = st.form_submit_button("更新")
                
                if submitted:
                    # フォーム入力された値を data_df に反映
                    for idx in missing_indices:
                        new_val = st.session_state.get(f"yvalue_{idx}", "").strip()
                        data_df.at[idx, Y_col_idx] = new_val
                    st.success("Y列の空欄更新が完了しました。")
                    
                    # 更新後の先頭3行をプレビュー
                    st.write("### ▼Y列更新後プレビュー（先頭3行）")
                    st.dataframe(data_df.head(3))
            else:
                st.info("Y列に空欄はありません。")

            # --------------------------------------------------
            # 2)～5) の変換処理を実行するボタン
            # --------------------------------------------------
            if st.button("変換を実行"):
                # --- (2) Y列を全角化 & 17文字以上を Z 列(26列目=0ベース25)へ ---
                Z_col_idx = 25
                for i in range(len(data_df)):
                    val_y = data_df.iat[i, Y_col_idx] or ""
                    # 全角化
                    full_val_y = to_fullwidth(val_y)

                    if len(full_val_y) >= 17:
                        data_df.iat[i, Y_col_idx] = full_val_y[:16]
                        data_df.iat[i, Z_col_idx] = full_val_y[16:]
                    else:
                        data_df.iat[i, Y_col_idx] = full_val_y

                # --- (3) Y列でソート ---
                data_df = data_df.sort_values(by=Y_col_idx, ascending=True, na_position='first')
                data_df.reset_index(drop=True, inplace=True)

                # --- (4) AZ列(52列目=0ベース51) に "007" を代入 ---
                AZ_col_idx = 51
                # 列数が足りない場合は増やす
                if AZ_col_idx >= data_df.shape[1]:
                    # 今ある列数より多い場合は空列を追加する
                    for _ in range(AZ_col_idx - data_df.shape[1] + 1):
                        data_df[data_df.shape[1]] = ""
                data_df[AZ_col_idx] = "007"

                # --- (5) ヘッダー行を上に戻す ---
                final_df = pd.concat([header_row.to_frame().T, data_df], ignore_index=True)

                st.write("### ▼変換後のデータプレビュー（先頭3行）")
                st.dataframe(final_df.head(3))

                # ダウンロード
                csv_str = final_df.to_csv(index=False, header=False, encoding="cp932")
                st.download_button(
                    label="変換後CSVをダウンロード",
                    data=csv_str.encode("cp932"),
                    file_name="converted.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"CSVの処理中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
