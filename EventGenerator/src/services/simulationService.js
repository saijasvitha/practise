
const {
    generateSimulationId,
    generateCorrelationId
} = require("../utils/idGenerator");

const {
    SCENARIOS
} = require("../utils/constants");

const {
    generateDatabaseFailureLogs
} = require("../scenarios/databaseFailure");

const {
    generateApiFailureLogs
} = require("../scenarios/apiFailure");

const {
    publishLog
} = require("../publishers/eventPublisher");

const SCENARIO_HANDLERS = {
    [SCENARIOS.DATABASE_FAILURE]: generateDatabaseFailureLogs,
    [SCENARIOS.API_FAILURE]: generateApiFailureLogs
};

const TOTAL_STEPS = 6;

const simulations = new Map();


// Start a new simulation
const startSimulation = ({
    scenario,
    durationSeconds = 60
}) => {

    // Validate scenario
    const scenarioHandler = SCENARIO_HANDLERS[scenario];

    if (!scenarioHandler) {
        throw new Error(`Unsupported scenario: ${scenario}`);
    }

    // Validate duration
    if (
        !Number.isFinite(durationSeconds) ||
        durationSeconds < 5 ||
        durationSeconds > 3600
    ) {
        throw new Error(
            "Duration must be between 5 and 3600 seconds"
        );
    }

    const simulationId = generateSimulationId();
    const correlationId = generateCorrelationId();

    // Six events distributed across the duration
    const intervalMs =
        (durationSeconds * 1000) / (TOTAL_STEPS - 1);

    const simulation = {
        simulationId,
        correlationId,
        scenario,
        status: "RUNNING",
        currentStep: -1,
        totalSteps: TOTAL_STEPS,
        startTime: new Date().toISOString(),
        endTime: null,
        durationSeconds,
        logs: [],
        latestMetrics: null,
        timer: null,
        error: null
    };

    simulations.set(simulationId, simulation);

    console.log(
        `Starting simulation: ${simulationId}`
    );

    // Schedule each stage progressively
    const executeStep = async (step) => {

        if (simulation.status !== "RUNNING") {
            return;
        }

        try {

            // Generate scenario-specific log
            const log = scenarioHandler({
                simulationId,
                correlationId,
                step
            });

            // Publish log to RabbitMQ
            await publishLog(log);

            // IMPORTANT:
            // Check whether the simulation was stopped
            // while RabbitMQ publishing was in progress.
            if (simulation.status !== "RUNNING") {
                return;
            }

            // Update simulation state after confirmation
            simulation.currentStep = step;
            simulation.logs.push(log);
            simulation.latestMetrics = {
                ...log.payload
            };

            console.log(
                `Simulation ${simulationId}: Step ${step} published`
            );

            // All six stages completed
            if (step === TOTAL_STEPS - 1) {

                simulation.status = "COMPLETED";
                simulation.endTime = new Date().toISOString();

                console.log(
                    `Simulation completed: ${simulationId}`
                );

                return;
            }

            // Schedule the next stage
            simulation.timer = setTimeout(() => {
                executeStep(step + 1);
            }, intervalMs);

        } catch (error) {

            // Do not overwrite STOPPED with FAILED
            if (simulation.status !== "RUNNING") {
                return;
            }

            simulation.status = "FAILED";
            simulation.error = error.message;
            simulation.endTime = new Date().toISOString();

            if (simulation.timer) {
                clearTimeout(simulation.timer);
                simulation.timer = null;
            }

            console.error(
                `Simulation failed: ${error.message}`
            );
        }
    };

    // Execute first stage immediately
    executeStep(0);

    return {
        simulationId,
        scenario,
        status: simulation.status,
        durationSeconds,
        totalSteps: TOTAL_STEPS,
        message: "Simulation started successfully"
    };
};


// Stop an active simulation
const stopSimulation = (simulationId) => {

    const simulation = simulations.get(simulationId);

    if (!simulation) {
        throw new Error("Simulation not found");
    }

    if (simulation.status !== "RUNNING") {
        throw new Error(
            `Cannot stop simulation with status: ${simulation.status}`
        );
    }

    if (simulation.timer) {
        clearTimeout(simulation.timer);
        simulation.timer = null;
    }

    simulation.status = "STOPPED";
    simulation.endTime = new Date().toISOString();

    console.log(
        `Simulation stopped: ${simulationId}`
    );

    return getSimulationStatus(simulationId);
};


// Get one simulation's status
const getSimulationStatus = (simulationId) => {

    const simulation = simulations.get(simulationId);

    if (!simulation) {
        throw new Error("Simulation not found");
    }

    return {
        simulationId: simulation.simulationId,
        scenario: simulation.scenario,
        status: simulation.status,
        currentStep: simulation.currentStep,
        totalSteps: simulation.totalSteps,
        durationSeconds: simulation.durationSeconds,
        startTime: simulation.startTime,
        endTime: simulation.endTime,
        error: simulation.error
    };
};


// Get all simulations
const getAllSimulations = () => {

    return Array.from(simulations.values()).map(simulation => ({
        simulationId: simulation.simulationId,
        scenario: simulation.scenario,
        status: simulation.status,
        currentStep: simulation.currentStep,
        totalSteps: simulation.totalSteps,
        startTime: simulation.startTime,
        endTime: simulation.endTime
    }));
};


// Get generated logs
const getSimulationLogs = (simulationId) => {

    const simulation = simulations.get(simulationId);

    if (!simulation) {
        throw new Error("Simulation not found");
    }

    return simulation.logs;
};


// Get latest metrics
const getSimulationMetrics = (simulationId) => {

    const simulation = simulations.get(simulationId);

    if (!simulation) {
        throw new Error("Simulation not found");
    }

    return simulation.latestMetrics;
};


module.exports = {
    startSimulation,
    stopSimulation,
    getSimulationStatus,
    getAllSimulations,
    getSimulationLogs,
    getSimulationMetrics
};
