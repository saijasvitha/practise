
const express = require("express");

const router = express.Router();

const {
    SCENARIOS
} = require("../utils/constants");

const {
    startSimulation,
    stopSimulation,
    getSimulationStatus,
    getAllSimulations,
    getSimulationLogs,
    getSimulationMetrics
} = require("../services/simulationService");


// GET: List available scenarios
router.get("/scenarios", (req, res) => {

    res.status(200).json({
        success: true,
        scenarios: Object.values(SCENARIOS)
    });

});


// POST: Start a simulation
router.post("/start", (req, res) => {

    try {

        const {
            scenario,
            durationSeconds = 60
        } = req.body;

        const result = startSimulation({
            scenario,
            durationSeconds
        });

        res.status(202).json({
            success: true,
            ...result
        });

    } catch (error) {

        res.status(400).json({
            success: false,
            message: error.message
        });

    }

});


// POST: Stop a simulation
router.post("/stop", (req, res) => {

    try {

        const { simulationId } = req.body;

        if (!simulationId) {
            return res.status(400).json({
                success: false,
                message: "simulationId is required"
            });
        }

        const result = stopSimulation(simulationId);

        res.status(200).json({
            success: true,
            message: "Simulation stopped successfully",
            data: result
        });

    } catch (error) {

        res.status(400).json({
            success: false,
            message: error.message
        });

    }

});


// GET: Simulation status
router.get("/status", (req, res) => {

    try {

        const { simulationId } = req.query;

        // Return all simulation summaries if no ID is provided
        if (!simulationId) {

            return res.status(200).json({
                success: true,
                simulations: getAllSimulations()
            });

        }

        const result = getSimulationStatus(simulationId);

        res.status(200).json({
            success: true,
            data: result
        });

    } catch (error) {

        res.status(404).json({
            success: false,
            message: error.message
        });

    }

});


// GET: Generated logs
router.get("/logs", (req, res) => {

    try {

        const { simulationId } = req.query;

        if (!simulationId) {
            return res.status(400).json({
                success: false,
                message: "simulationId is required"
            });
        }

        const logs = getSimulationLogs(simulationId);

        res.status(200).json({
            success: true,
            count: logs.length,
            logs
        });

    } catch (error) {

        res.status(404).json({
            success: false,
            message: error.message
        });

    }

});


// GET: Latest simulation metrics
router.get("/metrics", (req, res) => {

    try {

        const { simulationId } = req.query;

        if (!simulationId) {
            return res.status(400).json({
                success: false,
                message: "simulationId is required"
            });
        }

        const metrics = getSimulationMetrics(simulationId);

        res.status(200).json({
            success: true,
            metrics
        });

    } catch (error) {

        res.status(404).json({
            success: false,
            message: error.message
        });

    }

});


module.exports = router;
