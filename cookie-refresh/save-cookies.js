/**
 * 从浏览器导出的Cookie文件自动提取Cookie
 */
const fs = require('fs');
const path = require('path');

const COOKIE_FILE = '/Users/houzi/Downloads/gemini.google.com_cookies.txt';

function parseCookieFile(filePath) {
    if (!fs.existsSync(filePath)) {
        throw new Error(`Cookie文件不存在: ${filePath}`);
    }

    const content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split('\n');

    const cookies = {};

    for (const line of lines) {
        if (line.startsWith('#') || line.trim() === '') continue;

        const parts = line.split('\t');
        if (parts.length < 7) continue;

        const name = parts[5];
        const value = parts[6];

        if (name === '__Secure-1PSID') {
            cookies.SECURE_1PSID = value;
        } else if (name === '__Secure-1PSIDCC') {
            cookies.SECURE_1PSIDCC = value;
        } else if (name === '__Secure-1PSIDTS') {
            cookies.SECURE_1PSIDTS = value;
        }
    }

    return cookies;
}

function main() {
    console.log('════════════════════════════════════════');
    console.log('  保存Gemini Cookies');
    console.log('════════════════════════════════════════');
    console.log('');
    console.log(`📁 从文件读取: ${COOKIE_FILE}`);
    console.log('');

    try {
        const cookies = parseCookieFile(COOKIE_FILE);

        if (!cookies.SECURE_1PSID || !cookies.SECURE_1PSIDTS) {
            console.error('❌ Cookie文件中缺少必需的Cookie');
            console.error('   需要: __Secure-1PSID, __Secure-1PSIDTS');
            process.exit(1);
        }

        console.log('✅ 成功提取Cookies:');
        console.log(`   SECURE_1PSID: ${cookies.SECURE_1PSID.substring(0, 30)}...`);
        console.log(`   SECURE_1PSIDCC: ${cookies.SECURE_1PSIDCC?.substring(0, 30) || '(未找到)'}...`);
        console.log(`   SECURE_1PSIDTS: ${cookies.SECURE_1PSIDTS.substring(0, 30)}...`);
        console.log('');

        const cookieData = {
            SECURE_1PSID: cookies.SECURE_1PSID,
            SECURE_1PSIDCC: cookies.SECURE_1PSIDCC || '',
            SECURE_1PSIDTS: cookies.SECURE_1PSIDTS,
            timestamp: new Date().toISOString()
        };

        fs.writeFileSync(
            path.join(__dirname, 'cookies.json'),
            JSON.stringify(cookieData, null, 2)
        );

        console.log('✅ Cookies已保存到 cookies.json');
        console.log('');
        console.log('下一步: npm run sync');
        console.log('');

    } catch (error) {
        console.error('❌ 错误:', error.message);
        process.exit(1);
    }
}

main();
