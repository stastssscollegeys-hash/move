# TOOLS.md - Local Notes

## Git同期

### kaihatu1 リポへのpush
ワークスペースの変更を kaihatu1 リポに同期するコマンド:

```bash
cd "/Users/shimizusubaru/claude code/kaihatu1"
git add openclaw-workspace/
git commit -m "openclaw-workspace の変更を同期"
git push origin main
```

- **リポ**: https://github.com/subaru-blip/kaihatu1
- **ブランチ**: main
- **パス**: `openclaw-workspace/` 以下がワークスペース
- **注意**: `read` ツールではkaihatu1の外は触れないが、`exec`（シェルコマンド）なら `kaihatu1/` 内のgit操作が可能

### umarou アプリ（GitHub Pages）
- **リポ**: https://github.com/subaru-blip/umarou
- **公開URL**: https://subaru-blip.github.io/umarou/
- **パス**: `openclaw-workspace/umarou-app/`
- umarou リポへの直接pushも可能（独立リポとして残っている）

### 同期手順まとめ
1. ワークスペース内のファイルを編集
2. umarou アプリの変更 → `umarou-app/` 内で `git push`（GitHub Pages反映）
3. 全体の同期 → `kaihatu1/` で `git add openclaw-workspace/ && git push`
