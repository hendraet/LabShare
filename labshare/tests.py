from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django_webtest import WebTest
from labshare.models import Device, GPU, Reservation
from model_mommy import mommy


class TestLabshare(WebTest):

    csrf_checks = False

    def setUp(self):
        self.user = mommy.make(User)
        self.devices = mommy.make(Device, _quantity=3)
        mommy.make(GPU, device=self.devices[0], _quantity=2, used_memory="12 Mib", free_memory="100 Mib", total_memory="112 Mib")
        mommy.make(GPU, device=self.devices[1], used_memory="12 Mib", free_memory="100 Mib", total_memory="112 Mib")
        mommy.make(GPU, device=self.devices[-1], used_memory="12 Mib", free_memory="100 Mib", total_memory="112 Mib")

    def test_index(self):
        response = self.app.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

        for device in self.devices:
            self.assertIn(device.name, response.body.decode('utf-8'))

    def test_reserve_no_user(self):
        response = self.app.get(reverse("reserve"), expect_errors=True)
        self.assertEqual(response.status_code, 302)
        response = self.app.post(reverse("reserve"), expect_errors=True)
        self.assertEqual(response.status_code, 302)

    def test_reserve_get_user(self):
        response = self.app.get(reverse("reserve"), user=self.user)
        self.assertEqual(response.status_code, 200)

    def test_reserve_submit_form(self):
        response = self.app.get(reverse("reserve"), user=self.user)
        self.assertEqual(response.status_code, 200)

        form = response.form
        form["device"].force_value(self.devices[0].name)
        form["gpu"].force_value(self.devices[0].gpus.first().uuid)
        form["next-available-spot"] = "false"

        response = form.submit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reservation.objects.count(), 1)
        reservation = Reservation.objects.first()
        self.assertFalse(reservation.user_reserved_next_available_spot)

    def test_reserve_next_available_gpu_no_reserved_gpu(self):
        response = self.app.get(reverse("reserve"), user=self.user)
        self.assertEqual(response.status_code, 200)

        form = response.form
        form["device"].force_value(self.devices[0].name)
        form["gpu"].force_value(self.devices[0].gpus.first().uuid)
        form["next-available-spot"] = "true"

        response = form.submit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_reserve_next_available_gpu_one_reserved_gpu(self):
        mommy.make(Reservation, gpu=self.devices[0].gpus.first())

        response = self.app.get(reverse("reserve"), user=self.user)
        self.assertEqual(response.status_code, 200)

        form = response.form
        form["device"].force_value(self.devices[0].name)
        form["gpu"].force_value(self.devices[0].gpus.first().uuid)
        form["next-available-spot"] = "true"

        response = form.submit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reservation.objects.count(), 2)
        for gpu in self.devices[0].gpus.all():
            self.assertEqual(gpu.reservations.count(), 1)

    def test_reserve_next_available_gpu_two_reserved_gpus(self):
        for gpu in self.devices[0].gpus.all():
            mommy.make(Reservation, gpu=gpu)

        response = self.app.get(reverse("reserve"), user=self.user)
        self.assertEqual(response.status_code, 200)

        form = response.form
        form["device"].force_value(self.devices[0].name)
        form["gpu"].force_value(self.devices[0].gpus.first().uuid)
        form["next-available-spot"] = "true"

        response = form.submit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reservation.objects.count(), 4)
        self.assertEqual(Reservation.objects.filter(user_reserved_next_available_spot=True).count(), 2)
        for gpu in self.devices[0].gpus.all():
            self.assertEqual(gpu.reservations.count(), 2)

    def test_reserve_next_available_spot_one_gpu_no_reservation(self):
        response = self.app.get(reverse("reserve"), user=self.user)
        self.assertEqual(response.status_code, 200)

        form = response.form
        form["device"].force_value(self.devices[1].name)
        form["gpu"].force_value(self.devices[1].gpus.first().uuid)
        form["next-available-spot"] = "true"

        response = form.submit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_reserve_next_available_spot_one_gpu_reservation(self):
        mommy.make(Reservation, gpu=self.devices[1].gpus.first())

        response = self.app.get(reverse("reserve"), user=self.user)
        self.assertEqual(response.status_code, 200)

        form = response.form
        form["device"].force_value(self.devices[1].name)
        form["gpu"].force_value(self.devices[1].gpus.first().uuid)
        form["next-available-spot"] = "true"

        response = form.submit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reservation.objects.count(), 2)
        self.assertEqual(Reservation.objects.filter(user_reserved_next_available_spot=True).count(), 1)

    def test_get_gpu_info_no_user(self):
        response = self.app.get(
            "{url}?device_name={device_name}".format(url=reverse("gpus_for_device"), device_name=self.devices[0].name),
            expect_errors=True
        )
        self.assertEqual(response.status_code, 401)

    def test_get_gpu_info_no_ajax(self):
        response = self.app.get(
            "{url}?device_name={device_name}".format(url=reverse("gpus_for_device"), device_name=self.devices[0].name),
            expect_errors=True,
            user=self.user
        )
        self.assertEqual(response.status_code, 400)

    def test_get_gpu_wrong_method(self):
        response = self.app.post(
            "{url}?device_name={device_name}".format(url=reverse("gpus_for_device"), device_name=self.devices[0].name),
            expect_errors=True,
            user=self.user,
            xhr=True,
        )
        self.assertEqual(response.status_code, 400)

    def test_get_gpu_for_all_devices(self):
        for device in self.devices:
            response = self.app.get(
                "{url}?device_name={device_name}".format(url=reverse("gpus_for_device"), device_name=device.name),
                user=self.user,
                xhr=True,
            )
            self.assertEqual(response.status_code, 200)
            for gpu in device.gpus.all():
                self.assertIn(gpu.uuid, response.body.decode('utf-8'))
                self.assertIn(gpu.model_name, response.body.decode('utf-8'))

    def test_get_gpu_wrong_query_parameter(self):
        response = self.app.get(
            "{url}?bad={device_name}".format(url=reverse("gpus_for_device"), device_name=self.devices[0].name),
            user=self.user,
            expect_errors=True,
            xhr=True,
        )
        self.assertEqual(response.status_code, 400)

    def test_get_gpu_info_bad_requests(self):
        response = self.app.get(
            "{url}?uuid={uuid}".format(url=reverse("gpu_info"), uuid=self.devices[0].gpus.first().uuid),
            expect_errors=True
        )
        self.assertEqual(response.status_code, 401)

        response = self.app.get(
            "{url}?uuid={uuid}".format(url=reverse("gpu_info"), uuid=self.devices[0].gpus.first().uuid),
            expect_errors=True,
            xhr=True,
        )
        self.assertEqual(response.status_code, 401)

        response = self.app.get(
            "{url}?uuid={uuid}".format(url=reverse("gpu_info"), uuid=self.devices[0].gpus.first().uuid),
            expect_errors=True,
            user=self.user,
        )
        self.assertEqual(response.status_code, 400)

        response = self.app.post(
            "{url}?uuid={uuid}".format(url=reverse("gpu_info"), uuid=self.devices[0].gpus.first().uuid),
            expect_errors=True,
            user=self.user,
            xhr=True,
        )
        self.assertEqual(response.status_code, 400)

    def test_get_gpu_info_wrong_query_param(self):
        response = self.app.get(
            "{url}?bad={uuid}".format(url=reverse("gpu_info"), uuid=self.devices[0].gpus.first().uuid),
            expect_errors=True,
            user=self.user,
            xhr=True,
        )
        self.assertEqual(response.status_code, 400)

    def test_get_gpu_info_no_reservation(self):
        gpu = self.devices[0].gpus.first()
        response = self.app.get(
            "{url}?uuid={uuid}".format(url=reverse("gpu_info"), uuid=gpu.uuid),
            expect_errors=True,
            user=self.user,
            xhr=True,
        )
        self.assertEqual(response.status_code, 200)

        self.assertIn(gpu.free_memory, response.body.decode('utf-8'))
        self.assertIn(gpu.used_memory, response.body.decode('utf-8'))
        self.assertIn(gpu.total_memory, response.body.decode('utf-8'))
        self.assertIn("No current user", response.body.decode('utf-8'))

    def test_get_gpu_info_with_reservation(self):
        gpu = self.devices[0].gpus.first()
        mommy.make(Reservation, gpu=gpu, user=self.user)
        response = self.app.get(
            "{url}?uuid={uuid}".format(url=reverse("gpu_info"), uuid=gpu.uuid),
            expect_errors=True,
            user=self.user,
            xhr=True,
        )
        self.assertEqual(response.status_code, 200)

        self.assertIn(gpu.free_memory, response.body.decode('utf-8'))
        self.assertIn(gpu.used_memory, response.body.decode('utf-8'))
        self.assertIn(gpu.total_memory, response.body.decode('utf-8'))
        self.assertIn(self.user.username, response.body.decode('utf-8'))

    def test_gpu_done_no_user(self):
        response = self.app.get(reverse("done_with_gpu", args=[self.devices[0].gpus.first().id]))
        self.assertEqual(response.status_code, 302)

    def test_gpu_done_wrong_gpu_id(self):
        response = self.app.get(reverse("done_with_gpu", args=[17]), user=self.user, expect_errors=True)
        self.assertEqual(response.status_code, 404)

    def test_gpu_done_no_reservation(self):
        gpu = self.devices[0].gpus.first()
        response = self.app.get(reverse("done_with_gpu", args=[gpu.id]), user=self.user, expect_errors=True)
        self.assertEqual(response.status_code, 404)

    def test_gpu_done_reservation_wrong_user(self):
        gpu = self.devices[0].gpus.first()
        user = mommy.make(User)
        mommy.make(Reservation, gpu=gpu, user=user)

        response = self.app.get(reverse("done_with_gpu", args=[gpu.id]), user=self.user, expect_errors=True)
        self.assertEqual(response.status_code, 403)

    def test_gpu_done_only_one_reservation(self):
        gpu = self.devices[0].gpus.first()
        mommy.make(Reservation, gpu=gpu, user=self.user)

        response = self.app.get(reverse("done_with_gpu", args=[gpu.id]), user=self.user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reservation.objects.count(), 0)

    def test_gpu_done_one_more_reservation(self):
        gpu = self.devices[0].gpus.first()
        mommy.make(Reservation, _quantity=2, gpu=gpu, user=self.user, user_reserved_next_available_spot=False)

        response = self.app.get(reverse("done_with_gpu", args=[gpu.id]), user=self.user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_gpu_done_next_available_spot_reserved(self):
        user = mommy.make(User)
        gpus = self.devices[0].gpus
        mommy.make(Reservation, gpu=gpus.first(), user=self.user)
        mommy.make(Reservation, gpu=gpus.last(), user=self.user)
        mommy.make(Reservation, gpu=gpus.first(), user=user, user_reserved_next_available_spot=True)
        mommy.make(Reservation, gpu=gpus.last(), user=user, user_reserved_next_available_spot=True)
        self.assertEqual(Reservation.objects.count(), 4)

        response = self.app.get(reverse("done_with_gpu", args=[gpus.first().id]), user=self.user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reservation.objects.count(), 2)
        self.assertEqual(gpus.first().reservations.count(), 1)
        self.assertEqual(gpus.first().reservations.first().user, user)
        self.assertEqual(gpus.last().reservations.count(), 1)
        self.assertEqual(gpus.last().reservations.first().user, self.user)

    def test_gpu_done_next_available_spot_reserved_additional_reservation(self):
        user = mommy.make(User)
        gpus = self.devices[0].gpus
        mommy.make(Reservation, gpu=gpus.last(), user=self.user)
        mommy.make(Reservation, gpu=gpus.first(), user=self.user)
        mommy.make(Reservation, gpu=gpus.first(), user=user, user_reserved_next_available_spot=True)
        mommy.make(Reservation, gpu=gpus.last(), user=user, user_reserved_next_available_spot=True)
        mommy.make(Reservation, gpu=gpus.last(), user=self.user)
        self.assertEqual(Reservation.objects.count(), 5)

        response = self.app.get(reverse("done_with_gpu", args=[gpus.first().id]), user=self.user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reservation.objects.count(), 3)
        self.assertEqual(gpus.first().reservations.count(), 1)
        self.assertEqual(gpus.first().reservations.first().user, user)
        self.assertEqual(gpus.last().reservations.count(), 2)
        self.assertEqual(gpus.last().reservations.first().user, self.user)
        self.assertEqual(gpus.last().reservations.last().user, self.user)








