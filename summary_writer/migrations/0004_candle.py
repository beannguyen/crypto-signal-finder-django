# Generated by Django 2.0 on 2017-12-24 03:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('summary_writer', '0003_auto_20171217_1557'),
    ]

    operations = [
        migrations.CreateModel(
            name='Candle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('open', models.DecimalField(decimal_places=8, max_digits=50)),
                ('high', models.DecimalField(decimal_places=8, max_digits=50)),
                ('low', models.DecimalField(decimal_places=8, max_digits=50)),
                ('close', models.DecimalField(decimal_places=8, max_digits=50)),
                ('base_volume', models.DecimalField(decimal_places=8, max_digits=50)),
                ('volume', models.DecimalField(decimal_places=8, max_digits=50)),
                ('timestamp', models.DateTimeField()),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('market', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='summary_writer.Market')),
            ],
        ),
    ]
