-- 看最近产生了什么数据
SELECT *
FROM checkpoints
WHERE thread_id = 'durable-execution-postgres-001'
ORDER BY checkpoint_id DESC
LIMIT 20;