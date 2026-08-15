using System.Text.Json;

namespace LibreHardwareMonitorCollector;

public sealed record SensorRecord(
    string Identifier,
    string HardwareName,
    string HardwareType,
    string Name,
    string SensorType,
    float Value);

public sealed record CollectorSnapshot(DateTimeOffset Timestamp, IReadOnlyList<SensorRecord> Sensors);

public static class CollectorJson
{
    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        WriteIndented = false,
    };

    public static string Serialize(CollectorSnapshot snapshot) => JsonSerializer.Serialize(
        new
        {
            timestamp = snapshot.Timestamp.ToString("O"),
            sensors = snapshot.Sensors,
        },
        Options);
}
