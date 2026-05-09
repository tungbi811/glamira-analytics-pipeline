const range = db.summary.aggregate([
    { $group: {
        _id: null,
        min_time: { $min: "$time_stamp" },
        max_time: { $max: "$time_stamp" }
    }}
]).toArray()[0]

printjson({
    min_time: new Date(range.min_time * 1000),
    max_time: new Date(range.max_time * 1000)
})