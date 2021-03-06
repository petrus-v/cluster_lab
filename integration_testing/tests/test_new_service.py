import requests

from . import base_case
from . import cluster


class WhenDeployingANewServiceMasterSlave(base_case.ClusterTestCase):

    def given_a_cluster_without_test_service(self):
        self.application = cluster.Application(
            'https://github.com/mlfmonde/cluster_lab_test_service',
            'master'
        )
        self.cluster.cleanup_application(self.application)
        self.master = 'core1'
        self.slave = 'core2'

    def becauseWeDeployTheService(self):
        self.cluster.deploy_and_wait(
            master=self.master,
            slave=self.slave,
            application=self.application,
        )
        self.app = self.cluster.get_app_from_kv(self.application.app_key)

    def a_key_must_be_in_the_kv_store(self):
        self.assert_key_exists(self.application.app_key)

    def master_salve_should_be_correct_in_kv_store(self):
        assert (self.master, self.slave) == (self.app.master, self.app.slave)

    def kv_must_know_2_btrfs_volumes(self):
        assert len(self.app.volumes) == 2

    def btrfs_pg_volume_should_exists_only_on_master(self):
        self.assert_volume_exists_only_on(
            self.application.volume_prefix + 'dbdata',
            self.master,
            kind='btrfs'
        )

    def btrfs_anyblok_volume_should_exists_on_master(self):
        self.assert_volume_exists_only_on(
            self.application.volume_prefix + 'anyblok_data',
            self.master,
            kind='btrfs'
        )

    def cache_volume_must_exists_on_master(self):
        self.assert_volume_exists_only_on(
            self.application.volume_prefix + 'cache_data',
            self.master,
            kind='local'
        )

    def service_return_HTTP_code_200(self):
        '''we may add a dns server (bind9?) at some point to manage DNS'''
        session = requests.Session()
        response = session.get('http://service.cluster.lab')
        assert 200 == response.status_code
        session.close()

    def purge_pg_volume_must_be_scheduled(self):
        self.assert_btrfs_scheduled(
            'purge',
            self.application.volume_prefix + 'dbdata',
            [self.master, self.slave],
        )

    def purge_anyblok_volume_must_be_scheduled(self):
        self.assert_btrfs_scheduled(
            'purge',
            self.application.volume_prefix + 'anyblok_data',
            [self.master, self.slave],
        )

    def replicate_pg_volume_must_be_scheduled(self):
        self.assert_btrfs_scheduled(
            'replicate',
            self.application.volume_prefix + 'dbdata',
            [self.master],
        )

    def replicate_anyblok_volume_must_be_scheduled(self):
        self.assert_btrfs_scheduled(
            'replicate',
            self.application.volume_prefix + 'anyblok_data',
            [self.master],
        )

    def non_btrfs_volume_should_not_get_schedule(self):
        self.assert_btrfs_scheduled(
            '',
            self.application.volume_prefix + 'cache_data',
            [],
        )

    def consul_service_should_be_registered_on_the_master_node(self):
        self.assert_consul_service_on_node(
            self.application.name,
            self.master
        )

    def test_service_containers_should_run(self):
        self.assert_container_running_on(
            [self.app.ct.anyblok, self.app.ct.dbserver, ],
            [self.master]
        )
