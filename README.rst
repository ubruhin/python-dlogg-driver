python-dlogg-driver
===================

Unofficial python package to read data from a `Technische Alternative`_ `D-LOGG`_ device.


Installation
------------

.. code:: bash

  pip install dlogg-driver


Usage
-----

.. code:: python

  from dlogg_driver import DLoggDevice
  
  with DLoggDevice("/dev/ttyUSB0") as device:
      print u"Type: {}".format(device.get_type())
      print u"Firmware: {}".format(device.get_firmware_version())
      print u"Mode: {}".format(device.get_mode())
      print u"Logging criterion: {}".format(unicode(device.get_logging_criterion()))
      print u"Current data: {}".format(unicode(device.get_current_data()))
      header = device.get_header()
      print u"Number of available samples: {}".format(header.get_sample_count())
      data = device.fetch_data_range(header.start, 1)
      print u"Data [0]: {}".format(unicode(data[0]))
      device.fetch_end()


Credits
-------

- Many thanks to `Technische Alternative`_ for allowing me to create and publish
  this package under a free software license!
- Thanks also to H. Römer for publishing `d-logg-linux`_.


.. _`Technische Alternative`: http://www.ta.co.at/
.. _`D-LOGG`: http://www.ta.co.at/de/produkte/pc-anbindung/datenkonverter-d-logg.html
.. _`d-logg-linux`: http://d-logg-linux.roemix.de/
