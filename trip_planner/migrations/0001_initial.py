from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FuelStation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('truckstop_id', models.IntegerField()),
                ('name', models.CharField(max_length=200)),
                ('address', models.TextField()),
                ('city', models.CharField(max_length=100)),
                ('state', models.CharField(max_length=2)),
                ('rack_id', models.IntegerField()),
                ('retail_price', models.FloatField()),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
            ],
            options={
                'indexes': [models.Index(fields=['state'], name='trip_planne_state_d4a8e7_idx'), models.Index(fields=['retail_price'], name='trip_planne_retail__991152_idx')],
            },
        ),
        migrations.CreateModel(
            name='RouteCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_location', models.CharField(max_length=200)),
                ('end_location', models.CharField(max_length=200)),
                ('route_data', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'indexes': [models.Index(fields=['start_location', 'end_location'], name='trip_planne_start_l_f8e2d1_idx')],
                'unique_together': {('start_location', 'end_location')},
            },
        ),
    ]
