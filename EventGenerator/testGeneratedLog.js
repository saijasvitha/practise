
require("dotenv").config();

const {
    connectRabbitMQ,
    closeRabbitMQ
} = require("./src/config/rabbitmq");

const { generateLog } = require("./src/generators/logGenerator");

const { publishLog } = require("./src/publishers/eventPublisher");

const {
    generateSimulationId,
    generateCorrelationId
} = require("./src/utils/idGenerator");

const runTest = async () => {

    try {
        await connectRabbitMQ();

        const log = generateLog({
            simulationId: generateSimulationId(),
            correlationId: generateCorrelationId(),

            scenario: "DATABASE_FAILURE",
            service: "payment-service",
            severity: "WARN",

            message: "Database connection pool nearing capacity",

            payload: {
                activeConnections: 85,
                maxConnections: 100,
                waitingRequests: 15,
                averageLatencyMs: 1200,
                errorRate: 12.5
            }
        });

        console.log("Generated log:");
        console.log(JSON.stringify(log, null, 2));

        await publishLog(log);

        console.log("Generated log published to RabbitMQ!");

    } catch (error) {
        console.error("Test failed:", error.message);
        process.exitCode = 1;

    } finally {
        await closeRabbitMQ();
    }
};

runTest();
