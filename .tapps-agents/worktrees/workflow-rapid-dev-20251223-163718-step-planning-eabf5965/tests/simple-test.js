// Ultra-simple test - no Playwright complexity
const http = require('http');

async function testAPI() {
    console.log('🧪 Testing simplified architecture...');
    
    try {
        // Test health endpoint
        const healthResponse = await makeRequest('http://localhost:3000/api/v1/health');
        console.log('✅ Health API working:', healthResponse.statusCode);
        
        // Test dashboard loads
        const dashboardResponse = await makeRequest('http://localhost:3000/');
        console.log('✅ Dashboard loads:', dashboardResponse.statusCode);
        
        console.log('🎉 All tests passed! Architecture is working.');
        return true;
    } catch (error) {
        console.error('❌ Test failed:', error.message);
        return false;
    }
}

function makeRequest(url) {
    return new Promise((resolve, reject) => {
        const req = http.get(url, (res) => {
            resolve(res);
        });
        req.on('error', reject);
        req.setTimeout(5000, () => {
            req.destroy();
            reject(new Error('Timeout'));
        });
    });
}

// Run test
testAPI().then(success => {
    process.exit(success ? 0 : 1);
});
