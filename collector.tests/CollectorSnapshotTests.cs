using System.Text.Json;
using LibreHardwareMonitorCollector;
using Xunit;

namespace LibreHardwareMonitorCollector.Tests;

public sealed class CollectorSnapshotTests
{
    [Fact]
    public void MakeUnique_preserves_a_unique_library_identifier()
    {
        var used = new HashSet<string>();

        var identifier = SensorIdentifier.MakeUnique("/gpu-nvidia/0/load/0", "GPU Core", used);

        Assert.Equal("/gpu-nvidia/0/load/0", identifier);
    }

    [Fact]
    public void MakeUnique_disambiguates_duplicate_library_identifiers_by_sensor_name()
    {
        var used = new HashSet<string> { "/gpu-nvidia/0/load/3" };

        var identifier = SensorIdentifier.MakeUnique("/gpu-nvidia/0/load/3", "GPU Memory", used);

        Assert.Equal("/gpu-nvidia/0/load/3~gpu-memory", identifier);
    }

    [Fact]
    public void Serialize_emits_the_documented_sensor_contract()
    {
        var snapshot = new CollectorSnapshot(
            new DateTimeOffset(2026, 8, 14, 10, 0, 0, TimeSpan.Zero),
            [new SensorRecord("/cpu/temperature/0", "CPU", "Cpu", "Package", "Temperature", 50.5f)]);

        using var document = JsonDocument.Parse(CollectorJson.Serialize(snapshot));
        var root = document.RootElement;

        Assert.Equal("2026-08-14T10:00:00.0000000+00:00", root.GetProperty("timestamp").GetString());
        var sensor = Assert.Single(root.GetProperty("sensors").EnumerateArray());
        Assert.Equal("/cpu/temperature/0", sensor.GetProperty("identifier").GetString());
        Assert.Equal("Temperature", sensor.GetProperty("sensor_type").GetString());
        Assert.Equal(50.5, sensor.GetProperty("value").GetDouble());
    }
}
