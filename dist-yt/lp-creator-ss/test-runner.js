"use strict";
// ===== LP Creator SS - Test Runner =====
// Claude Codeから直接テストするためのCLIスクリプト
// 使い方: node dist-yt/lp-creator-ss/test-runner.js '{"heroHeadline":"...", ...}'
// または: node dist-yt/lp-creator-ss/test-runner.js --from-file copy.json
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const service_1 = require("./service");
const OUTPUT_DIR = path_1.default.join(__dirname, '..', '..', 'output', 'lp-creator-test');
function main() {
    const args = process.argv.slice(2);
    if (args.length === 0) {
        console.log(`
LP Creator テストランナー
========================

使い方:
  1. JSONファイルから:
     node dist-yt/lp-creator-ss/test-runner.js --from-file <path-to-json>

  2. JSON文字列を直接:
     node dist-yt/lp-creator-ss/test-runner.js '<json-string>'

  3. デフォルトテストデータで:
     node dist-yt/lp-creator-ss/test-runner.js --demo

出力先: ${OUTPUT_DIR}/
`);
        process.exit(0);
    }
    let copyJson;
    if (args[0] === '--demo') {
        copyJson = getDemoData();
        console.log('[Demo] デフォルトテストデータを使用');
    }
    else if (args[0] === '--from-file') {
        const filePath = args[1];
        if (!filePath || !fs_1.default.existsSync(filePath)) {
            console.error(`ファイルが見つかりません: ${filePath}`);
            process.exit(1);
        }
        const raw = fs_1.default.readFileSync(filePath, 'utf-8');
        copyJson = JSON.parse(raw);
        console.log(`[File] ${filePath} から読み込み`);
    }
    else {
        copyJson = JSON.parse(args[0]);
        console.log('[JSON] コマンドライン引数から読み込み');
    }
    // renderHTMLは設定ストアを参照するがAPIは叩かない
    const service = new service_1.LPCreatorService();
    const html = service.renderHTML(copyJson);
    // 出力
    if (!fs_1.default.existsSync(OUTPUT_DIR)) {
        fs_1.default.mkdirSync(OUTPUT_DIR, { recursive: true });
    }
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const outputPath = path_1.default.join(OUTPUT_DIR, `lp-test-${timestamp}.html`);
    fs_1.default.writeFileSync(outputPath, html, 'utf-8');
    console.log(`\n✔ LP HTML を保存しました: ${outputPath}`);
    console.log(`  ファイルサイズ: ${(Buffer.byteLength(html) / 1024).toFixed(1)} KB`);
    // JSONも保存（再利用のため）
    const jsonPath = path_1.default.join(OUTPUT_DIR, `lp-test-${timestamp}.json`);
    fs_1.default.writeFileSync(jsonPath, JSON.stringify(copyJson, null, 2), 'utf-8');
    console.log(`  コピーJSON: ${jsonPath}`);
}
function getDemoData() {
    return {
        heroHeadline: 'たった3入力でプロ品質のLPが完成',
        heroSubheadline: '面倒なコーディングもデザインも不要。AIが30秒で仕上げます',
        heroCta: '今すぐ無料で試す',
        problemSection: [
            'LPを作りたいが、デザイナーに頼む予算がない',
            'テンプレートを買ったが、結局カスタマイズできずに放置している',
            '文章が書けない。何を書けばいいのかわからない',
        ],
        solutionSection: 'LP Creatorは、商品名・ターゲット・強みの3つを入力するだけで、コピーライティングのプロが書いたような文章とデザインを自動生成します。AIDA・PASなどの実績あるフレームワークを組み込み、心理トリガーも計算済み。',
        benefitsSection: [
            { title: '30秒で完成', description: 'AIがリアルタイムにコピーを生成。待ち時間はほぼゼロ。' },
            { title: 'プロ品質のデザイン', description: 'モバイル対応のレスポンシブLP。コーディング知識不要。' },
            { title: '心理学ベース', description: 'AIDA・PAS・FABなど4つのフレームワークと5つの心理トリガーを自動適用。' },
        ],
        socialProofSection: [
            { name: 'M.T.様 30代 個人起業家', text: '外注で20万円かかっていたLPが、5分で完成しました。しかもコンバージョン率は外注時より高い。正直、驚いています。' },
            { name: 'K.S.様 40代 コンサルタント', text: 'セミナーの集客LPに使いました。参加者から「プロに頼んだの？」と聞かれるクオリティで大満足です。' },
        ],
        featuresSection: [
            { title: 'AIコピーライティング', description: '商品の強みを自動でベネフィットに変換。売れる文章をAIが執筆。' },
            { title: 'ワンクリックHTML出力', description: '生成されたLPはそのままHTML/CSSとしてダウンロード可能。' },
            { title: 'リアルタイムプレビュー', description: 'AIが書いている様子をリアルタイムで確認。完成後は即プレビュー。' },
        ],
        faqSection: [
            { question: '初心者でも使えますか？', answer: 'はい。商品名・ターゲット・強みの3つを入力するだけなので、パソコンが使える方なら誰でもお使いいただけます。' },
            { question: '生成されたLPは商用利用できますか？', answer: 'はい。生成されたHTML/CSSは自由にお使いいただけます。著作権はご利用者様に帰属します。' },
            { question: 'どのくらいの時間で完成しますか？', answer: '通常30秒以内に完成します。入力を含めても5分あれば十分です。' },
        ],
        urgencySection: '期間限定：今なら全機能を無料でお試しいただけます。この機会をお見逃しなく。',
        finalCtaSection: {
            headline: '今すぐ、あなたのLPを作りましょう',
            subheadline: '3つの入力だけで、プロ品質のLPが手に入ります',
            buttonText: '無料でLPを作成する',
        },
    };
}
main();
