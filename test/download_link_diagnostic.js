// 下载链接实时诊断脚本
// 用于追踪从翻译完成到下载链接生成的全过程

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function diagnosticDownloadLink() {
    console.log('=== 下载链接生成实时诊断 ===\n');

    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // 启用详细日志记录
    page.on('console', msg => {
        const text = msg.text();
        if (text.includes('download') || text.includes('链接') || text.includes('href') || text.includes('complete')) {
            console.log(`[浏览器控制台] ${msg.type()}: ${text}`);
        }
    });

    // 监听网络请求，捕获所有与下载相关的请求
    page.on('request', request => {
        const url = request.url();
        if (url.includes('download') || url.includes('/api/')) {
            console.log(`[网络请求] ${request.method()} ${url}`);
        }
    });

    // 监听响应
    page.on('response', async (response) => {
        const url = response.url();
        if (url.includes('download')) {
            console.log(`[网络响应] ${response.status()} ${url}`);
            try {
                const text = await response.text();
                console.log(`[响应内容预览] ${text.substring(0, 200)}...`);
            } catch (e) {
                console.log(`[响应内容] 无法读取`);
            }
        }
    });

    try {
        console.log('1. 访问主页...');
        await page.goto('http://localhost:5001/', { waitUntil: 'networkidle' });
        console.log('   ✅ 页面加载完成\n');

        // 检查初始下载链接状态
        console.log('2. 检查初始下载链接状态...');
        const initialHref = await page.evaluate(() => {
            const link = document.querySelector('#download-link');
            return link ? link.getAttribute('href') : 'NOT_FOUND';
        });
        console.log(`   初始 href: ${initialHref}\n`);

        // 上传测试文件
        console.log('3. 上传测试文件...');
        const testFilePath = path.join(__dirname, '../test_documents/TESTING_GUIDE_simple.md');
        if (!fs.existsSync(testFilePath)) {
            console.log(`   ❌ 测试文件不存在: ${testFilePath}`);
            return false;
        }

        await page.setInputFiles('input[type="file"]', testFilePath);
        console.log('   ✅ 文件已选择\n');

        // 等待文件上传处理
        await page.waitForTimeout(1000);
        console.log('4. 点击翻译按钮...');
        await page.click('#translate-btn');
        console.log('   ✅ 翻译已开始\n');

        // 监听SSE消息，捕获complete事件
        console.log('5. 监听翻译进度和下载链接生成...');
        let downloadLinkCaptured = null;
        let finalHref = null;

        // 方法1: 监听控制台日志
        page.on('console', msg => {
            const text = msg.text();
            if (text.includes('data: complete:')) {
                console.log(`   [SSE消息] ${text}`);
                const match = text.match(/data: complete:(.+)/);
                if (match) {
                    const filename = match[1].trim();
                    console.log(`   [解析文件名] ${filename}`);
                    console.log(`   [预期下载链接] /api/download/${filename}`);
                }
            }
        });

        // 方法2: 直接检查DOM变化
        const checkDownloadLink = async () => {
            try {
                const link = await page.$('#download-link');
                if (link) {
                    const href = await link.evaluate(el => el.getAttribute('href'));
                    if (href && href !== '#' && href !== downloadLinkCaptured) {
                        downloadLinkCaptured = href;
                        console.log(`   [DOM变化] 下载链接已更新: ${href}`);

                        // 验证链接格式
                        if (href.startsWith('/api/download/')) {
                            console.log('   ✅ 链接格式正确 (包含 /api 前缀)');
                        } else {
                            console.log('   ❌ 链接格式错误 (缺少 /api 前缀)');
                            console.log(`   实际: ${href}`);
                            console.log(`   期望: /api/download/...`);
                        }
                    }
                }
            } catch (e) {
                // 忽略错误
            }
        };

        // 定期检查下载链接状态
        for (let i = 0; i < 60; i++) {
            await page.waitForTimeout(1000);
            await checkDownloadLink();

            // 检查是否有完成标识
            const progressText = await page.textContent('#progress-log');
            if (progressText && progressText.includes('翻译完成')) {
                console.log('\n6. 检测到"翻译完成"标识');
                finalHref = await page.evaluate(() => {
                    const link = document.querySelector('#download-link');
                    return link ? link.getAttribute('href') : 'NOT_FOUND';
                });
                console.log(`   最终下载链接: ${finalHref}`);
                break;
            }
        }

        console.log('\n7. 验证下载链接...');
        if (finalHref && finalHref !== '#') {
            if (finalHref.startsWith('/api/download/')) {
                console.log('   ✅ 下载链接格式正确');
                console.log(`   链接: ${finalHref}`);

                // 尝试访问下载链接
                console.log('\n8. 测试下载链接可访问性...');
                const testUrl = `http://localhost:5001${finalHref}`;
                try {
                    const response = await page.goto(testUrl, { waitUntil: 'networkidle', timeout: 5000 });
                    console.log(`   HTTP状态: ${response.status()}`);
                    if (response.status() === 200) {
                        console.log('   ✅ 链接可正常访问');
                    } else {
                        console.log('   ❌ 链接访问失败');
                    }
                } catch (e) {
                    console.log(`   ❌ 链接访问异常: ${e.message}`);
                }
            } else {
                console.log('   ❌ 下载链接格式错误');
                console.log(`   实际: ${finalHref}`);
                console.log('   期望: /api/download/文件名');
            }
        } else {
            console.log('   ❌ 未找到有效的下载链接');
        }

        console.log('\n=== 诊断完成 ===');
        console.log('\n总结:');
        console.log(`- 初始链接: ${initialHref}`);
        console.log(`- 最终链接: ${finalHref || '未生成'}`);

        if (finalHref && finalHref.startsWith('/api/download/')) {
            console.log('\n✅ 下载功能正常 - 链接包含 /api 前缀');
        } else if (finalHref) {
            console.log('\n❌ 下载功能异常 - 链接缺少 /api 前缀');
            console.log('   这可能是以下原因造成的:');
            console.log('   1. 前端JavaScript代码中有错误的链接生成逻辑');
            console.log('   2. 浏览器缓存了旧版本的页面');
            console.log('   3. 存在多个版本的模板文件');
        }

        await browser.close();
        return finalHref && finalHref.startsWith('/api/download/');

    } catch (error) {
        console.error('诊断过程中发生错误:', error);
        await browser.close();
        return false;
    }
}

// 运行诊断
diagnosticDownloadLink().then(success => {
    process.exit(success ? 0 : 1);
}).catch(error => {
    console.error('诊断脚本执行失败:', error);
    process.exit(1);
});
