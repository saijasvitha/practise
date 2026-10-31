
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
        message: "Database connection established successfully"
    },
    {
        severity: SEVERITIES.INFO,
        message: "Database connection usage increasing"
    },
    {
        severity: SEVERITIES.INFO,
        message: "Database connection pool showing increased activity"
    },
    {
        severity: SEVERITIES.WARN,
        message: "Database connection pool nearing capacity"
    },
    {
        severity: SEVERITIES.ERROR,
        message: "Database connection pool critically overloaded"
    },
    {
        severity: SEVERITIES.ERROR,
        message: "Database connection pool exhausted. Requests timing out"
    }
];

const generateDatabaseFailureLogs = ({
    simulationId,
    correlationId,
    step
}) => {

    const result = generateMetrics(
        SCENARIOS.DATABASE_FAILURE,
        step
    );

    const logConfig = LOG_MESSAGES[step];

    const log = generateLog({
        simulationId,
        correlationId,

        scenario: SCENARIOS.DATABASE_FAILURE,

        service: SERVICES.PAYMENT,

        severity: logConfig.severity,

        message: logConfig.message,

        payload: {
            stage: result.stage,
            ...result.metrics
        }
    });

    return log;
};

module.exports = {
    generateDatabaseFailureLogs
};
