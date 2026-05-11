db.summary.aggregate([
    { $group: { _id: "$collection", count: { $sum: 1 } } },
    { $sort: { count: -1 } }
]).forEach(doc => print(doc._id + ": " + doc.count))