
const {
    generateMetrics
} = require("../generators/metricsGenerator");

const {
    generateLog
} = require("../generators/logGenerator");

const {
    SCENARIOS,
    SERVICES,
    SEVERITIES
} = require("../utils/constants");

const LOG_MESSAGES = [
    {
        severity: SEVERITIES.INFO,
        message: "Payment gateway connection established successfully"
    },
    {
        severity: SEVERITIES.INFO,
        message: "Payment gateway response time increasing"
    },
    {
        severity: SEVERITIES.WARN,
        message: "Payment gateway experiencing intermittent delays"
    },
    {
        severity: SEVERITIES.WARN,
        message: "Payment gateway timeout rate exceeding normal threshold"
    },
    {
        severity: SEVERITIES.ERROR,
        message: "Payment gateway experiencing significant request failures"
    },
    {
        severity: SEVERITIES.ERROR,
        message: "Payment gateway unavailable. Most requests are failing"
    }
];

const generateApiFailureLogs = ({
    simulationId,
    correlationId,
    step
}) => {

    const result = generateMetrics(
        SCENARIOS.API_FAILURE,
        step
    );

    const logConfig = LOG_MESSAGES[step];

    const log = generateLog({
        simulationId,
        correlationId,

        scenario: SCENARIOS.API_FAILURE,

        service: SERVICES.PAYMENT,

        severity: logConfig.severity,

        message: logConfig.message,

        payload: {
            stage: result.stage,
            externalService: "payment-gateway",
            ...result.metrics
        }
    });

    return log;
};

module.exports = {
    generateApiFailureLogs
};
