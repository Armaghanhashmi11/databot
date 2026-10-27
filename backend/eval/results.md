# Eval Results

## Summary

| Model | Accuracy | Correct/Total | Avg Latency (ms) | p50 Latency (ms) | Errors |
|---|---|---|---|---|---|
| ollama/qwen2.5:7b | 90% | 9/10 | 5210 | 5172 | 0 |
| ollama/llama3.1:8b | 70% | 7/10 | 7397 | 4411 | 0 |

## Per-question detail

### ollama/qwen2.5:7b

| # | Question | Correct | Latency (ms) | Answer |
|---|---|---|---|---|
| 1 | How many orders are in the dataset? | yes | 4669 | in the dataset, there are 20 orders. |
| 2 | How many unique customers placed orders? | yes | 6270 | The number of unique customers who placed orders is 20. |
| 3 | What is the total quantity sold in the Electronics category? | yes | 5881 | The total quantity sold in the Electronics category is 23. |
| 4 | Which region has the highest total revenue, where revenue is quantity times unit_price? | yes | 4898 | The region with the highest total revenue is the West region, with a total revenue of $869.85. |
| 5 | What is the average unit_price across all orders, rounded to two decimals? | yes | 4738 | $51.00 |
| 6 | How many orders came from the South region? | yes | 5278 | There were 5 orders that came from the South region. |
| 7 | Which product was ordered most frequently, counting number of orders per product? | yes | 5399 | The product 'Gadget X' was ordered most frequently, with a total of 6 orders. |
| 8 | Which category has more total revenue: Hardware or Electronics? | yes | 5067 | The category with more total revenue is Electronics, with a total revenue of $1699.77, compared to Hardware, which has a total revenue of $759.68. |
| 9 | What are the earliest and latest order_date values in the dataset? | no | 5747 | The earliest order_date in the dataset is January 5, 2025, and the latest order_date is March 1, 2025. |
| 10 | How many orders had a quantity greater than 3? | yes | 4150 | 6 orders had a quantity greater than 3. |

### ollama/llama3.1:8b

| # | Question | Correct | Latency (ms) | Answer |
|---|---|---|---|---|
| 1 | How many orders are in the dataset? | yes | 34084 | 20 |
| 2 | How many unique customers placed orders? | no | 4182 | } |
| 3 | What is the total quantity sold in the Electronics category? | no | 4755 | Some quantity sold in the Electronics category is 10. |
| 4 | Which region has the highest total revenue, where revenue is quantity times unit_price? | yes | 4126 | West |
| 5 | What is the average unit_price across all orders, rounded to two decimals? | yes | 4473 | 50.99 |
| 6 | How many orders came from the South region? | yes | 4689 | The number of orders from the South region is 5. |
| 7 | Which product was ordered most frequently, counting number of orders per product? | yes | 4035 | Gadget X |
| 8 | Which category has more total revenue: Hardware or Electronics? | no | 5077 | Hardware |
| 9 | What are the earliest and latest order_date values in the dataset? | yes | 4348 | The earliest order_date value in the dataset is 2025-01-05, and the latest order_date value is 2025-03-01. |
| 10 | How many orders had a quantity greater than 3? | yes | 4204 | 6 |
