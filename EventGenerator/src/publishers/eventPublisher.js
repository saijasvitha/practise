
const { getChannel } = require("../config/rabbitmq");

const EXCHANGE = process.env.RABBITMQ_EXCHANGE;
const ROUTING_KEY = "log.generated";

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

const delay = ms =>
    new Promise(resolve => setTimeout(resolve, ms));

const publishLog = async (logEvent) => {

    if (!logEvent || typeof logEvent !== "object" || Array.isArray(logEvent)) {
        throw new Error("Invalid log event");
    }

    if (logEvent.eventType !== "LOG_GENERATED") {
        throw new Error("Invalid event type");
    }

    if (!logEvent.eventId || !logEvent.simulationId) {
        throw new Error("Missing event identifiers");
    }

    if (!EXCHANGE) {
        throw new Error("RabbitMQ exchange is not configured");
    }

    const channel = getChannel();

    const message = Buffer.from(JSON.stringify(logEvent));

    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {

        let returnedError = null;

        const handleReturn = (returnedMessage) => {
            if (returnedMessage.properties.messageId === logEvent.eventId) {
                returnedError = new Error(
                    `Message was not routed to a queue: ${logEvent.eventId}`
                );
            }
        };

        channel.on("return", handleReturn);

        try {

            channel.publish(
                EXCHANGE,
                ROUTING_KEY,
                message,
                {
                    persistent: true,
                    mandatory: true,
                    contentType: "application/json",
                    messageId: logEvent.eventId,
                    timestamp: Date.now(),
                    type: logEvent.eventType
                }
            );

            await channel.waitForConfirms();

            // Allow a returned unroutable message to be detected.
            await new Promise(resolve => setImmediate(resolve));

            if (returnedError) {
                throw returnedError;
            }

            console.log(
                `Log published successfully: ${logEvent.eventId}`
            );

            return true;

        } catch (error) {

            console.error(
                `Publishing attempt ${attempt} failed:`,
                error.message
            );

            if (attempt === MAX_RETRIES) {
                throw error;
            }

            await delay(RETRY_DELAY_MS);

        } finally {
            channel.removeListener("return", handleReturn);
        }
    }
};

module.exports = {
    publishLog
};
