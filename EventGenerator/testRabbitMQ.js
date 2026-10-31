
const {
    connectRabbitMQ,
    closeRabbitMQ
} = require("./src/config/rabbitmq");

const testConnection = async () => {
    try {
        await connectRabbitMQ();

        console.log("SUCCESS: RabbitMQ is ready!");

    } catch (error) {
        console.error("FAILED:", error.message);
        process.exitCode = 1;

    } finally {
        await closeRabbitMQ();
    }
};

testConnection();
