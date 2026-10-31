
const {
    generateEventId,
    generateSimulationId,
    generateCorrelationId
} = require("../utils/idGenerator");

const {
    EVENT_TYPES,
    SEVERITIES,
    SCENARIOS
} = require("../utils/constants");

const generateLog = ({
    simulationId,
    correlationId,
    scenario,
    service,
    severity,
    message,
    payload = {}
}) => {

    // Validate required fields
    if (!scenario || !service || !severity || !message) {
        throw new Error("Missing required log fields");
    }

    // Validate scenario
    if (!Object.values(SCENARIOS).includes(scenario)) {
        throw new Error(`Invalid scenario: ${scenario}`);
    }

    // Validate severity
    if (!Object.values(SEVERITIES).includes(severity)) {
        throw new Error(`Invalid severity: ${severity}`);
    }

    if (
        typeof payload !== "object" ||
        payload === null ||
        Array.isArray(payload)
    ) {
        throw new Error("Payload must be a valid object");
    }

    // Construct common event envelope
    const logEvent = {
        eventId: generateEventId(),

        eventType: EVENT_TYPES.LOG_GENERATED,

        simulationId: simulationId || generateSimulationId(),

        correlationId: correlationId || generateCorrelationId(),

        timestamp: new Date().toISOString(),

        scenario,

        service,

        severity,

        payload: {
            message,
            ...payload
        }
    };

    return logEvent;
};

module.exports = {
    generateLog
};
