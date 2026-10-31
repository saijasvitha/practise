
require("dotenv").config();

const express = require("express");
const cors = require("cors");

const {
    connectRabbitMQ,
    closeRabbitMQ
} = require("./config/rabbitmq");

const simulatorRoutes = require("./routes/simulatorRoutes");

const app = express();

const PORT = process.env.PORT || 5000;


// Middleware
app.use(cors());
app.use(express.json());


// Health check
app.get("/health", (req, res) => {

    res.status(200).json({
        success: true,
        message: "EventGenerator is running",
        service: "Production Failure Simulator"
    });

});


// Simulator APIs
app.use("/api/simulator", simulatorRoutes);


// Start server
const startServer = async () => {

    try {

        // Connect to RabbitMQ before accepting requests
        await connectRabbitMQ();

        const server = app.listen(PORT, () => {

            console.log("----------------------------------");
            console.log("EventGenerator server started");
            console.log(`Server running on port ${PORT}`);
            console.log("----------------------------------");

        });

        // Graceful shutdown
        const shutdown = async () => {

            console.log("Shutting down EventGenerator...");

            server.close(async () => {

                try {
                    await closeRabbitMQ();
                    process.exit(0);

                } catch (error) {
                    console.error("Shutdown error:", error.message);
                    process.exit(1);
                }

            });

        };

        process.once("SIGINT", shutdown);
        process.once("SIGTERM", shutdown);

    } catch (error) {

        console.error(
            "Failed to start EventGenerator:",
            error.message
        );

        await closeRabbitMQ().catch(() => {});

        process.exit(1);

    }

};

startServer();
