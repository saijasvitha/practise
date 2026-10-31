
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
