// Simple deployment validation script
const http = require('http');

async function validateDeployment() {
    console.log('🔍 Validating complete deployment...');
    
    const results = [];
    
    // Test dashboard
    try {
        const dashboardResponse = await makeRequest('http://localhost:3000/');
        results.push({ service: 'Dashboard', status: dashboardResponse.statusCode, working: dashboardResponse.statusCode === 200 });
    } catch (error) {
        results.push({ service: 'Dashboard', status: 'ERROR', working: false, error: error.message });
    }
    
    // Test API health
    try {
        const apiResponse = await makeRequest('http://localhost:3000/api/v1/health');
        const isJSON = apiResponse.data.startsWith('{');
        results.push({ service: 'API Health', status: apiResponse.statusCode, working: apiResponse.statusCode === 200 && isJSON });
    } catch (error) {
        results.push({ service: 'API Health', status: 'ERROR', working: false, error: error.message });
    }
    
    // Test WebSocket service
    try {
        const wsResponse = await makeRequest('http://localhost:8001/health');
        results.push({ service: 'WebSocket Service', status: wsResponse.statusCode, working: wsResponse.statusCode === 200 });
    } catch (error) {
        results.push({ service: 'WebSocket Service', status: 'ERROR', working: false, error: error.message });
    }
    
    // Test Enrichment Pipeline
    try {
        const enrichResponse = await makeRequest('http://localhost:8002/health');
        results.push({ service: 'Enrichment Pipeline', status: enrichResponse.statusCode, working: enrichResponse.statusCode === 200 });
    } catch (error) {
        results.push({ service: 'Enrichment Pipeline', status: 'ERROR', working: false, error: error.message });
    }
    
    // Test Admin API
    try {
        const adminResponse = await makeRequest('http://localhost:8003/api/v1/health');
        results.push({ service: 'Admin API', status: adminResponse.statusCode, working: adminResponse.statusCode === 200 });
    } catch (error) {
        results.push({ service: 'Admin API', status: 'ERROR', working: false, error: error.message });
    }
    
    // Display results
    console.log('\n📊 Deployment Status:');
    console.log('====================');
    
    let allWorking = true;
    results.forEach(result => {
        const status = result.working ? '✅' : '❌';
        console.log(`${status} ${result.service}: ${result.status}`);
        if (result.error) {
            console.log(`   Error: ${result.error}`);
        }
        if (!result.working) allWorking = false;
    });
    
    console.log('\n🎯 Summary:');
    if (allWorking) {
        console.log('✅ All services are working! Dashboard should display data.');
        console.log('🌐 Access dashboard at: http://localhost:3000');
    } else {
        console.log('❌ Some services are not working. Check the errors above.');
    }
    
    return allWorking;
}

function makeRequest(url) {
    return new Promise((resolve, reject) => {
        const req = http.get(url, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve({ statusCode: res.statusCode, data }));
        });
        req.on('error', reject);
        req.setTimeout(10000, () => {
            req.destroy();
            reject(new Error('Timeout'));
        });
    });
}

// Run validation
validateDeployment().then(success => {
    process.exit(success ? 0 : 1);
});
