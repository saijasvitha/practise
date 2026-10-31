
const { randomUUID } = require("crypto");

// Generate unique IDs with readable prefixes
const generateId = (prefix) => {
    return `${prefix}-${randomUUID()}`;
};

const generateEventId = () => generateId("evt");

const generateSimulationId = () => generateId("sim");

const generateCorrelationId = () => generateId("corr");

module.exports = {
    generateEventId,
    generateSimulationId,
    generateCorrelationId
};
