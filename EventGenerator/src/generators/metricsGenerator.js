
const { SCENARIOS } = require("../utils/constants");

const STAGES = [
    "NORMAL",
    "NORMAL",
    "DEGRADED",
    "WARNING",
    "CRITICAL",
    "FAILURE"
];

// Each array represents metric values from step 0 to step 5.
const METRIC_PROFILES = {

    [SCENARIOS.DATABASE_FAILURE]: [
        {
            activeConnections: 20,
            maxConnections: 100,
            waitingRequests: 0,
            averageLatencyMs: 80,
            errorRate: 0.1
        },
        {
            activeConnections: 35,
            maxConnections: 100,
            waitingRequests: 2,
            averageLatencyMs: 150,
            errorRate: 0.5
        },
        {
            activeConnections: 55,
            maxConnections: 100,
            waitingRequests: 8,
            averageLatencyMs: 450,
            errorRate: 2.5
        },
        {
            activeConnections: 75,
            maxConnections: 100,
            waitingRequests: 20,
            averageLatencyMs: 1200,
            errorRate: 8.5
        },
        {
            activeConnections: 90,
            maxConnections: 100,
            waitingRequests: 35,
            averageLatencyMs: 3000,
            errorRate: 22.5
        },
        {
            activeConnections: 100,
            maxConnections: 100,
            waitingRequests: 50,
            averageLatencyMs: 5200,
            errorRate: 45.2
        }
    ],

    [SCENARIOS.MEMORY_LEAK]: [
        {
            memoryUsageMB: 300,
            heapUsedMB: 200,
            heapTotalMB: 500,
            heapUsagePercent: 40,
            memoryGrowthRateMBPerMinute: 0
        },
        {
            memoryUsageMB: 450,
            heapUsedMB: 300,
            heapTotalMB: 500,
            heapUsagePercent: 60,
            memoryGrowthRateMBPerMinute: 15
        },
        {
            memoryUsageMB: 600,
            heapUsedMB: 420,
            heapTotalMB: 600,
            heapUsagePercent: 70,
            memoryGrowthRateMBPerMinute: 25
        },
        {
            memoryUsageMB: 800,
            heapUsedMB: 640,
            heapTotalMB: 800,
            heapUsagePercent: 80,
            memoryGrowthRateMBPerMinute: 40
        },
        {
            memoryUsageMB: 950,
            heapUsedMB: 855,
            heapTotalMB: 1000,
            heapUsagePercent: 85.5,
            memoryGrowthRateMBPerMinute: 55
        },
        {
            memoryUsageMB: 1200,
            heapUsedMB: 1140,
            heapTotalMB: 1200,
            heapUsagePercent: 95,
            memoryGrowthRateMBPerMinute: 75
        }
    ],

    [SCENARIOS.API_FAILURE]: [
        {
            totalRequests: 1000,
            successfulRequests: 995,
            failedRequests: 5,
            timeoutRate: 0.1,
            successRate: 99.5,
            averageResponseTimeMs: 100
        },
        {
            totalRequests: 1000,
            successfulRequests: 970,
            failedRequests: 30,
            timeoutRate: 2,
            successRate: 97,
            averageResponseTimeMs: 250
        },
        {
            totalRequests: 1000,
            successfulRequests: 900,
            failedRequests: 100,
            timeoutRate: 8,
            successRate: 90,
            averageResponseTimeMs: 700
        },
        {
            totalRequests: 1000,
            successfulRequests: 750,
            failedRequests: 250,
            timeoutRate: 20,
            successRate: 75,
            averageResponseTimeMs: 1500
        },
        {
            totalRequests: 1000,
            successfulRequests: 500,
            failedRequests: 500,
            timeoutRate: 40,
            successRate: 50,
            averageResponseTimeMs: 3000
        },
        {
            totalRequests: 1000,
            successfulRequests: 100,
            failedRequests: 900,
            timeoutRate: 85,
            successRate: 10,
            averageResponseTimeMs: 8000
        }
    ],

    [SCENARIOS.BAD_DEPLOYMENT]: [
        {
            deploymentVersion: "v1.0.0",
            totalRequests: 1000,
            failedRequests: 2,
            errorRate: 0.2,
            successfulRequests: 998
        },
        {
            deploymentVersion: "v1.1.0",
            totalRequests: 1000,
            failedRequests: 10,
            errorRate: 1,
            successfulRequests: 990
        },
        {
            deploymentVersion: "v1.1.0",
            totalRequests: 1000,
            failedRequests: 50,
            errorRate: 5,
            successfulRequests: 950
        },
        {
            deploymentVersion: "v1.1.0",
            totalRequests: 1000,
            failedRequests: 150,
            errorRate: 15,
            successfulRequests: 850
        },
        {
            deploymentVersion: "v1.1.0",
            totalRequests: 1000,
            failedRequests: 350,
            errorRate: 35,
            successfulRequests: 650
        },
        {
            deploymentVersion: "v1.1.0",
            totalRequests: 1000,
            failedRequests: 700,
            errorRate: 70,
            successfulRequests: 300
        }
    ],

    [SCENARIOS.MICROSERVICE_LATENCY]: [
        {
            averageLatencyMs: 80,
            p95LatencyMs: 150,
            p99LatencyMs: 250,
            affectedRequests: 0,
            errorRate: 0.1
        },
        {
            averageLatencyMs: 150,
            p95LatencyMs: 300,
            p99LatencyMs: 500,
            affectedRequests: 20,
            errorRate: 0.5
        },
        {
            averageLatencyMs: 400,
            p95LatencyMs: 800,
            p99LatencyMs: 1200,
            affectedRequests: 100,
            errorRate: 2
        },
        {
            averageLatencyMs: 900,
            p95LatencyMs: 1800,
            p99LatencyMs: 2500,
            affectedRequests: 300,
            errorRate: 5
        },
        {
            averageLatencyMs: 1800,
            p95LatencyMs: 3500,
            p99LatencyMs: 5000,
            affectedRequests: 600,
            errorRate: 15
        },
        {
            averageLatencyMs: 3500,
            p95LatencyMs: 7000,
            p99LatencyMs: 10000,
            affectedRequests: 900,
            errorRate: 30
        }
    ]
};

// Generate metrics for a particular scenario and progression step.
const generateMetrics = (scenario, step = 0) => {

    const profile = METRIC_PROFILES[scenario];

    if (!profile) {
        throw new Error(`Unsupported scenario: ${scenario}`);
    }

    if (
        !Number.isInteger(step) ||
        step < 0 ||
        step >= profile.length
    ) {
        throw new Error("Step must be an integer between 0 and 5");
    }

    return {
        scenario,
        step,
        stage: STAGES[step],
        metrics: { ...profile[step] },
        generatedAt: new Date().toISOString()
    };
};

module.exports = {
    generateMetrics,
    STAGES
};
