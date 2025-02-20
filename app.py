import streamlit as st
import pandas as pd
import mojimoji

def to_fullwidth(s: str) -> str:
    """半角→全角変換"""
    if not isinstance(s, str):
        return s
    return mojimoji.han_to_zen(s, ascii=True, digit=True, kana=True)

def main():
    st.title("Y列空欄を入力して変換するサンプル")

    uploaded_file = st.file_uploader("CSVをアップロード", type=["csv"])
    if not uploaded_file:
        st.stop()

    # ヘッダーなしで読み込み、1行目を見出し行扱い・2行目以降をデータとして使う
    df_raw = pd.read_csv(uploaded_file, encoding="cp932", header=None, dtype=str)
    if df_raw.shape[0] < 2:
        st.warning("2行目以降のデータがありません。")
        st.stop()

    # 1行目（ヘッダー）と、2行目以降（データ）を分割
    header_row = df_raw.iloc[0].copy()
    data_df = df_raw.iloc[1:].copy().reset_index(drop=True)

    # 各種列インデックス
    #   - Y列(25列目) → 0ベースで24
    #   - Z列(26列目) → 0ベースで25
    #   - ここでは「6列目の注文者氏名」を 0ベースで 5 と仮定（実際のCSVに合わせて修正してください）
    Y_COL_IDX = 24
    Z_COL_IDX = 25
    NAME_COL_IDX = 5  # 「どの注文か分かるように表示したい氏名が入っている列」

    # 空欄のY列をフォームで入力してもらう（1行ずつ）
    data_df[Y_COL_IDX] = data_df[Y_COL_IDX].fillna("")
    missing_mask = data_df[Y_COL_IDX].str.strip() == ""
    missing_indices = data_df[missing_mask].index

    st.write("### ▼ データプレビュー（先頭3行）")
    st.dataframe(data_df.head(3))

    # ▼ フォーム開始
    #   「変換を実行」ボタンが押されると、そのタイミングで Y列更新＆変換処理までやる
    with st.form("fill_y_and_convert"):
        if len(missing_indices) > 0:
            st.warning(f"Y列が空欄の行が {len(missing_indices)} 件あります。値を入力してください。")

            for idx in missing_indices:
                # 6列目の氏名(例: NAME_COL_IDX=5)を取得して表示
                name_val = data_df.iat[idx, NAME_COL_IDX] or ""
                current_y = data_df.iat[idx, Y_COL_IDX] or ""
                st.text_input(
                    label=f"行 {idx} / 注文者：{name_val} の Y列",
                    key=f"y_input_{idx}",
                    value=current_y
                )
        else:
            st.info("Y列に空欄はありません。必要がなければそのまま変換実行できます。")

        # フォーム内のボタンを1つにまとめ、押すと同時にY列更新＆変換
        do_transform = st.form_submit_button("Y列を更新して変換を実行")

        if do_transform:
            # ▼ 1) Y列を更新（フォーム入力値をDataFrameに反映）
            for idx in missing_indices:
                new_val = st.session_state.get(f"y_input_{idx}", "").strip()
                data_df.iat[idx, Y_COL_IDX] = new_val

            # ▼ 2) 変換処理
            #     (a) 全角化 & 17文字目以降をZ列へ
            for i in range(len(data_df)):
                val_y = data_df.iat[i, Y_COL_IDX] or ""
                full_val = to_fullwidth(val_y)
                if len(full_val) >= 17:
                    data_df.iat[i, Y_COL_IDX] = full_val[:16]
                    data_df.iat[i, Z_COL_IDX] = full_val[16:]
                else:
                    data_df.iat[i, Y_COL_IDX] = full_val

            #     (b) Y列で昇順ソート
            data_df.sort_values(by=Y_COL_IDX, inplace=True)
            data_df.reset_index(drop=True, inplace=True)

            #     (c) AZ列(52列目=0ベース51) に "001" をセット
            AZ_COL_IDX = 51
            # 列数が足りない場合は空列を追加
            if AZ_COL_IDX >= data_df.shape[1]:
                for _ in range(AZ_COL_IDX - data_df.shape[1] + 1):
                    data_df[data_df.shape[1]] = ""
            data_df[AZ_COL_IDX] = "001"

            #     (d) ヘッダーを結合
            final_df = pd.concat([header_row.to_frame().T, data_df], ignore_index=True)

            st.success("Y列の更新＆変換が完了しました！")
            st.write("### ▼ 変換後データ（先頭3行）")
            st.dataframe(final_df.head(3))

            # ダウンロードボタン
            csv_str = final_df.to_csv(index=False, header=False, encoding="cp932")
            st.download_button(
                label="変換後CSVをダウンロード",
                data=csv_str.encode("cp932"),
                file_name="converted.csv",
                mime="text/csv"
            )

            # 処理完了したので break 的に抜ける
            st.stop()

if __name__ == "__main__":
    main()
