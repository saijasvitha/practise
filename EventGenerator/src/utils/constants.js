
const EVENT_TYPES = {
    LOG_GENERATED: "LOG_GENERATED"
};

const SEVERITIES = {
    INFO: "INFO",
    WARN: "WARN",
    ERROR: "ERROR"
};

const SCENARIOS = {
    DATABASE_FAILURE: "DATABASE_FAILURE",
    API_FAILURE: "API_FAILURE"
};

const SERVICES = {
    PAYMENT: "payment-service",
    API_GATEWAY: "api-gateway"
};

const ROUTING_KEYS = {
    LOG_GENERATED: "log.generated"
};

module.exports = {
    EVENT_TYPES,
    SEVERITIES,
    SCENARIOS,
    SERVICES,
    ROUTING_KEYS
};
