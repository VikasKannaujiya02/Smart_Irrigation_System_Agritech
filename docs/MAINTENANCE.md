# Maintenance Manual

## Regular Maintenance Tasks

### Daily
1. Check system health via `/health` endpoint
2. Review alerts and resolve any issues
3. Verify sensors are reporting data

### Weekly
1. Create a full system backup
2. Review logs for errors or warnings
3. Check water usage statistics
4. Clean sensor nodes (remove dirt/debris)

### Monthly
1. Test pump operation
2. Verify battery levels of sensor nodes
3. Review and update irrigation schedule
4. Check for software updates

## Log Management

Logs are stored in the `logs/` directory. Log rotation is configured to:
- Keep logs up to 100MB per file
- Keep up to 20 backup log files

To view logs:
```bash
# Live tail
tail -f logs/irrigation.log

# View recent logs
tail -n 100 logs/irrigation.log
```

## Backup Management

Backups are stored in `data/sqlite/backups/`. Automated backups can be configured in the system settings.

### Retention Policy
- Keep last 7 daily backups
- Keep last 4 weekly backups
- Keep last 12 monthly backups

### Manual Backup
```bash
# Via API
curl -X POST http://localhost:8000/api/backup/create

# Via Dashboard
Settings > Backup > Create Backup
```

## Sensor Maintenance

### Soil Moisture Sensors
- Clean sensors monthly
- Calibrate at least once per season
- Replace batteries when < 20%

### NPK Sensors
- Clean sensor probe after each use
- Store in dry place when not in use
- Calibrate with standard solutions annually

### Pump Maintenance
- Check for leaks monthly
- Lubricate moving parts quarterly
- Replace filters annually

## Troubleshooting Guide

### System Health Warnings
- **High CPU usage**: Check for runaway processes, review AI model inference frequency
- **High memory usage**: Increase memory allocation, reduce data retention period
- **Low disk space**: Clean old backups, rotate logs

### Sensor Issues
- **No data**: Check LoRa connection, verify sensor battery
- **Inaccurate readings**: Clean sensor, recalibrate
- **Sensor drift**: Use sensor drift detection, recalibrate or replace

### Database Issues
- **Corruption**: Restore from backup, run integrity check
- **Slow queries**: Optimize queries, add indexes

## Security Checklist

- Regularly update dependencies
- Rotate API keys
- Use HTTPS in production
- Restrict access to backend
- Keep firmware up to date
- Regular security audits
