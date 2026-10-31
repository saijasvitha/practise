
const amqp = require("amqplib");
require("dotenv").config();

let connection = null;
let channel = null;

const connectRabbitMQ = async () => {
    try {
        console.log("Connecting to RabbitMQ...");

        connection = await amqp.connect(
            process.env.RABBITMQ_URL
        );

        console.log("RabbitMQ connected successfully!");

        // Create publisher confirm channel
        channel = await connection.createConfirmChannel();

        // Create durable topic exchange
        await channel.assertExchange(
            process.env.RABBITMQ_EXCHANGE,
            "topic",
            { durable: true }
        );

        // Create durable log queue
        await channel.assertQueue(
            process.env.LOG_QUEUE,
            { durable: true }
        );

        // Bind log queue to exchange
        await channel.bindQueue(
            process.env.LOG_QUEUE,
            process.env.RABBITMQ_EXCHANGE,
            "log.generated"
        );

        console.log("RabbitMQ exchange configured!");
        console.log("Log queue configured!");
        console.log("Log routing key configured!");

        return channel;

    } catch (error) {
        console.error("RabbitMQ connection error:", error.message);
        throw error;
    }
};

const getChannel = () => {
    if (!channel) {
        throw new Error("RabbitMQ channel not initialized");
    }

    return channel;
};

const closeRabbitMQ = async () => {
    if (channel) {
        await channel.close();
        channel = null;
    }

    if (connection) {
        await connection.close();
        connection = null;
    }

    console.log("RabbitMQ connection closed");
};

module.exports = {
    connectRabbitMQ,
    getChannel,
    closeRabbitMQ
};
