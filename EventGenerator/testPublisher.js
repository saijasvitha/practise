
require("dotenv").config();

const {
    connectRabbitMQ,
    closeRabbitMQ
} = require("./src/config/rabbitmq");

const { publishLog } = require("./src/publishers/eventPublisher");

const testPublisher = async () => {

    try {
        // Establish RabbitMQ connection
        await connectRabbitMQ();

        // Sample production log
        const testLog = {
            eventId: "evt-test-001",
            eventType: "LOG_GENERATED",
            simulationId: "sim-test-001",
            correlationId: "corr-test-001",
            timestamp: new Date().toISOString(),
            scenario: "DATABASE_FAILURE",
            service: "payment-service",
            severity: "WARN",

            payload: {
                message: "Database connection pool nearing capacity",
                activeConnections: 85,
                maxConnections: 100,
                connectionUsage: 85,
                waitingRequests: 15,
                averageLatencyMs: 1200,
                errorRate: 12.5
            }
        };

        // Publish log
        await publishLog(testLog);

        console.log("Test log successfully sent!");

    } catch (error) {

        console.error("Test failed:", error.message);
        process.exitCode = 1;

    } finally {

        await closeRabbitMQ();

    }
};

testPublisher();
