
const {
    generateMetrics,
    STAGES
} = require("./src/generators/metricsGenerator");

const scenarios = [
    "DATABASE_FAILURE",
    "MEMORY_LEAK",
    "API_FAILURE",
    "BAD_DEPLOYMENT",
    "MICROSERVICE_LATENCY"
];

for (const scenario of scenarios) {

    console.log("\n====================================");
    console.log(`SCENARIO: ${scenario}`);
    console.log("====================================");

    for (let step = 0; step <= 5; step++) {

        const result = generateMetrics(scenario, step);

        console.log(`\nSTEP ${step} - ${STAGES[step]}`);

        console.log(
            JSON.stringify(result.metrics, null, 2)
        );
    }
}
