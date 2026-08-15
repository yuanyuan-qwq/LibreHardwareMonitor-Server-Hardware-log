using LibreHardwareMonitor.Hardware;

namespace LibreHardwareMonitorCollector;

public static class HardwareSnapshotReader
{
    public static CollectorSnapshot Collect()
    {
        var computer = new Computer
        {
            IsCpuEnabled = true,
            IsGpuEnabled = true,
            IsMemoryEnabled = true,
            IsMotherboardEnabled = true,
            IsStorageEnabled = true,
        };
        try
        {
            computer.Open();
            computer.Accept(new UpdateVisitor());
            var sensors = new List<SensorRecord>();
            var usedIdentifiers = new HashSet<string>(StringComparer.Ordinal);
            foreach (var hardware in computer.Hardware)
                AddHardwareSensors(hardware, sensors, usedIdentifiers);
            return new CollectorSnapshot(DateTimeOffset.Now, sensors);
        }
        finally
        {
            computer.Close();
        }
    }

    private static void AddHardwareSensors(
        IHardware hardware,
        ICollection<SensorRecord> sensors,
        ISet<string> usedIdentifiers)
    {
        foreach (var sensor in hardware.Sensors)
        {
            if (sensor.Value is not float value)
                continue;
            sensors.Add(new SensorRecord(
                SensorIdentifier.MakeUnique(sensor.Identifier.ToString(), sensor.Name, usedIdentifiers),
                hardware.Name,
                hardware.HardwareType.ToString(),
                sensor.Name,
                sensor.SensorType.ToString(),
                value));
        }
        foreach (var child in hardware.SubHardware)
            AddHardwareSensors(child, sensors, usedIdentifiers);
    }

    private sealed class UpdateVisitor : IVisitor
    {
        public void VisitComputer(IComputer computer) => computer.Traverse(this);

        public void VisitHardware(IHardware hardware)
        {
            hardware.Update();
            foreach (var child in hardware.SubHardware)
                child.Accept(this);
        }

        public void VisitSensor(ISensor sensor) { }

        public void VisitParameter(IParameter parameter) { }
    }
}
