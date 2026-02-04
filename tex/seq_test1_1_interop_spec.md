# `.seq` ⇄ `test1_1` 相互変換 仕様書（SurfaceSpec / ReportConfig / SeqConditions）

この仕様書は、`ex_CodeV/` 配下の CODE V 形式 `.seq` を **`test1_1` 形式**（`SurfaceSpec` / `ReportConfig`）へ変換し、さらに **逆変換（YAML・.seq への書き戻し）**を行うための仕様をまとめたものです。

- **方針（重要）**
  1. `SurfaceSpec` / `ReportConfig` は **汚さない**（`.seq` 固有のコマンド列を追加しない）
  2. `.seq` のうち **面に紐づかない行**（例：`DIM M`, `WTW ...`, `INI ...`, `CA`, `PIM`, `GO` など）は **`SeqConditions` に保持**
  3. 相互変換（往復）を壊さないため、`CCY/THC/CIR/EDG` などの **面直後に出る行**も `SeqConditions` 側で保持する
  4. `SurfaceSpec`, `ReportConfig`, `SeqConditions` は **YAML で読み書きできる API** を提供する

---

## 1. 対象ファイルとモジュール

### 1.1 入力 `.seq`
- `ex_CodeV/petzval.seq`
- `ex_CodeV/microscope.seq`
- 将来的には同ディレクトリ配下の他 `.seq` にも適用

### 1.2 実装モジュール（想定）
- `optics/seq_convert.py`  
  `.seq` の parse / 書き戻し / `ReportConfig` 構築等を担当
- `optics/yaml_io.py`  
  `SurfaceSpec`, `ReportConfig`, `SeqConditions` の YAML IO を担当
- `tests_seq_roundtrip.py`  
  `petzval.seq` / `microscope.seq` を用いた往復テスト・YAMLテスト

---

## 2. データモデル（YAML 可能な構造）

### 2.1 SurfaceSpec（既存、汚さない）
レンズ処方（面列）を表す最小構造。

- `num`: 面番号（1,2,3,...）
- `R`: 曲率半径
- `t`: 面後厚み（次面まで）
- `glass`: ガラス名（例：`N-BK7_schott`、空気なら `air`）
- `stop`: 絞り面フラグ

> `.seq` 固有の補助コマンド（`CCY/THC/CIR/EDG...`）は持たせない。

### 2.2 ReportConfig（既存、汚さない）
ABCD/主平面レポート計算の設定。

- `prescription`: `List[SurfaceSpec]`
- `wavelengths_nm`: `List[float]`（中間波長が参照となる運用を想定）
- `start_surface`: ABCD積算開始面
- `end_surface`: ABCD積算終了面
- `image_surface`: 像面（SI）面番号
- `image_z_abs`: 像面 z を絶対指定する場合
- `reference_surface`: z=0 の基準面
- `opticspy_root`: 屈折率取得のための optispy ルート（任意）

### 2.3 SeqConditions（`.seq` 側の条件・メタ保持）
`.seq` のうち **面定義（SO/S/SI/STO）以外**の情報を保持する。

推奨フィールド（最低限）：

- `title: str`
- `dim: str | None`（例：`DIM M` の M）
- `wavelengths: List[float]`（`WL ...`）
- `yan_deg: List[float]`（`YAN ...`）
- `xan_deg: List[float]`（`XAN ...`）
- `epd: float | None`（`EPD ...`）
- `fno: float | None`（`FNO ...`）
- `na: float | None`（`NA ...`）
- `nao: float | None`（`NAO ...` のような派生コマンド用）
- `raw_cmds: List[str]`  
  面に紐づかないコマンド行を **出現順で保持**（例：`INI ...`, `WTW ...`, `WTF ...`, `CA`, `PIM`, `GO`, `RDM`, `LEN`, `DER ...` など）
- `surface_cmds: Dict[int, List[str]]`  
  面直後の補助行（例：`CCY`, `THC`, `CIR`, `CIR EDG`, `EDG`, `CUY` 等）を **面番号に紐付けて保持**
- `plane_surfaces: List[int]`  
  入力 `.seq` で `R=0`（平面）だった面番号を記録し、書き戻しで `R=0` を復元できるようにする

> `surface_cmds` に `STO` を保存しても良いが、**モデル側（SurfaceSpec.stop）を正**とし、書き戻し時に stop 面に `STO` を出す。

---

## 3. `.seq` パース仕様（.seq → SeqDocument）

`.seq` を 1本読み込み、次を返す構造を想定：

- `SeqDocument` = `{ prescription: List[SurfaceSpec], conditions: SeqConditions }`

### 3.1 行継続（重要：microscope.seq）
- 行末が `&` の場合、次行を連結して 1 行として処理する
- 連結後に改行を 1 つに正規化する

### 3.2 `;` による複合コマンド
- 例：`CCY 0 ; THC 0` のような行がありうる
- パーサは **`;` で分割**し、各セグメントを独立コマンドとして扱えるようにする  
  （ただし、`raw_cmds` には原文を保持する設計も可。相互変換の忠実度と簡便性で選択）

### 3.3 面行（SO / S / SI）
- `SO`, `S`, `SI` で始まる行は面行として扱う
- フォーマット（サブセット）  
  `SO R t [glass]` / `S R t [glass]` / `SI R t [glass]`
- `glass` が無い場合：`air`
- `R == 0` の場合：内部表現は `R = 10000000.0` とし、同時に `plane_surfaces` に該当面番号を記録する

面番号 `num` は、面行が出現した順に `1..N` を自動採番する。

### 3.4 STO（絞り面）
- `STO` は **直前の面**に適用される
- パース結果：該当 `SurfaceSpec.stop = True` にする
- 併せて `surface_cmds[num]` に `STO` を保持してもよい（ただし stop の正は SurfaceSpec）

### 3.5 それ以外の行（面に紐づかない）
- 次のような行は **SeqConditions に格納**する（SurfaceSpec/ReportConfigには入れない）
  - 例：`DIM M`, `WTW ...`, `INI ...`, `CA`, `PIM`, `GO`, `RDM`, `LEN`, `DER ...`, `REF ...`, `WTF ...`, `VUX/VUY/VLX/VLY ...`, `NAO ...` 等
- 保持方法：
  - まずは `raw_cmds` に **出現順でそのまま**保存（最も安全）

### 3.6 面直後に現れる補助行（surface_cmds）
`CCY`, `THC`, `CIR`, `CIR EDG`, `EDG`, `CUY` 等は、典型的に面行の直後に現れる。

- これらは **直前の面番号**に紐付けて `surface_cmds[num]` に追加する
- 今後、より忠実な位置復元が必要なら、`raw_cmds` 側にも残しつつ “位置情報付き” に拡張する

---

## 4. `.seq` 書き戻し仕様（SeqDocument → .seq）

### 4.1 基本方針
- 書き戻しは **正規化された** `.seq` になる（元ファイルと行単位で完全一致する必要はない）
- ただし、以下の意味的同値は保証する：
  - 面列（`R/t/glass/stop`）が同一
  - `WL/XAN/YAN/EPD/FNO/NA/NAO/DIM` 等の主要条件が保持される
  - `raw_cmds` が保持される（少なくとも再出力される）
  - `surface_cmds` が適切な面に紐付いて再出力される
  - `plane_surfaces` を参照して `R=0` の復元ができる

### 4.2 出力順（推奨）
1. `TITLE`（あれば）
2. `DIM`（あれば）
3. `WL`, `EPD`, `XAN`, `YAN`, `FNO`, `NA`, `NAO`（あれば）
4. `raw_cmds` のうち「面より前に出したいもの」  
   ※現段階は簡略化し、`raw_cmds` は末尾にまとめて出してもよい（忠実度を上げたい場合は位置情報を保持する）
5. 面列：`SO`（1面目）→ `S`（中間）→ `SI`（最終）
6. 各面の直後に `surface_cmds[num]` を出力
7. stop 面の場合：面の直後に `STO` を出力
8. `raw_cmds` の残り（例：`PIM`, `GO`, `DER ...` 等）

---

## 5. `.seq` → ReportConfig 構築規約

`.seq` は慣習的に

- 1面目が `SO`（物体面）
- 最終面が `SI`（像面）

とみなせるため、ABCD 解析用の `ReportConfig` は以下で生成する。

- `reference_surface = 2`
- `start_surface = 2`
- `image_surface = N`（最終面）
- `end_surface = N - 1`（像面直前まで）
- `wavelengths_nm = conditions.wavelengths`

> 波長単位（nm/µm）は `.seq` の内容に依存する可能性があるため、運用で統一すること。  
> 内部を nm に統一するなら、パース時に変換する。

---

## 6. 描画条件（example3/4 と test1_1 の整合）

### 6.1 field_angles_deg の決め方
- 優先：`conditions.yan_deg`
- 次点：`conditions.xan_deg`
- どちらも無ければ `[0.0]`

### 6.2 fno の決め方
- `conditions.fno` があればそれ
- 無ければ呼び出し側で `fallback_fno` を指定する（example3/4 はスクリプト側で `Lens.FNO = ...` を上書きしている）

---

## 7. YAML IO API 仕様

すべて `yaml.safe_dump / safe_load` を使用し、以下の関数を提供する。

- `dump_surface_specs(path, specs)` / `load_surface_specs(path) -> List[SurfaceSpec]`
- `dump_report_config(path, cfg)` / `load_report_config(path) -> ReportConfig`
- `dump_seq_conditions(path, cond)` / `load_seq_conditions(path) -> SeqConditions`
- `dump_seq_document(path, doc)` / `load_seq_document(path) -> SeqDocument`（任意）

### 7.1 YAML の目視ポイント
- `*.specs.yaml`：面列（`R/t/glass/stop`）が正しく落ちているか
- `*.cond.yaml`：面に紐づかない行（`DIM/WTW/INI/CA/PIM/GO/...`）が `raw_cmds` に入っているか  
  面直後の行（`CCY/THC/CIR...`）が `surface_cmds[num]` に入っているか
- `*.cfg.yaml`：`start/end/image/reference` の規約が意図どおりか

---

## 8. テスト仕様（petzval / microscope）

### 8.1 round-trip テスト（.seq ↔ doc ↔ .seq）
対象：`petzval.seq`, `microscope.seq`

1. `.seq` を parse して `SeqDocument` を得る
2. `SeqDocument` から `.seq` 文字列を生成
3. 生成した `.seq` を再パースして `SeqDocument` を得る
4. 以下が一致することを確認
   - `prescription`（面数・R/t/glass・stop）
   - 主要条件（WL/YAN/XAN/EPD/FNO/NA/NAO/DIM 等）
   - `surface_cmds` の面番号対応（保持している場合）
   - `plane_surfaces` により `R=0` が復元できること（writer実装に依存）

### 8.2 YAML round-trip テスト
1. `SurfaceSpec`, `ReportConfig`, `SeqConditions`, `SeqDocument` を YAML に dump
2. 再 load して同値性を確認

### 8.3 KEEP_YAML（目視確認用）
`tests_seq_roundtrip.py` は通常 temp ディレクトリを使うが、目視確認のため

- `KEEP_YAML=1` を付けて実行すると `out_yaml/` に YAML を残す

例：
```bash
KEEP_YAML=1 python tests_seq_roundtrip.py
# out_yaml/petzval/{specs,cond,cfg,doc}.yaml
# out_yaml/microscope/{specs,cond,cfg,doc}.yaml
```

出力先を変えたい場合（実装している場合）：
```bash
KEEP_YAML=1 YAML_DIR=debug_yaml python tests_seq_roundtrip.py
```

---

## 9. 既知の制限と拡張ポイント

- `.seq` のコマンドは本来非常に多い。現在は「opticspy の簡易サブセット＋メタ保持」にフォーカスしている。
- `raw_cmds` は「順序保持」で安全だが、書き戻しの忠実度（位置復元）を上げるには **位置情報**（面の前/後、特定面の直前など）を保持する拡張が有効。
- `PIM` の厳密な意味再現は CODE V の solve/設定体系に依存するため、当面は `raw_cmds` として保持・再出力に留める。

---

## 10. 期待される利用手順（推奨）

1. `.seq` を parse → `SeqDocument`（処方＋条件）
2. `SeqDocument.conditions` から `field_angles_deg / fno` を決定して描画・解析に利用
3. `SeqDocument` から `ReportConfig` を構築して ABCD/主平面レポートを計算
4. YAML に dump してバージョン管理・検証
5. YAML から再構築して `.seq` に書き戻し（往復確認）

---

以上。
